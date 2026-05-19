# metrics/evaluate_batch.py
import os, json, asyncio, time, pandas as pd
from typing import Dict, Any
from tqdm import tqdm
import httpx

import metrics as M

API_URL = os.getenv("SUMMARY_API", "http://localhost:8000/summarize")
DEFAULT_MODO = int(os.getenv("DEFAULT_MODO", "30"))

def load_long_texts(path_txt: str) -> Dict[str, str]:
    docs, doc_id, buf = {}, None, []
    with open(path_txt, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("===DOC_ID:"):
                if doc_id is not None:
                    docs[doc_id] = "\n".join(buf).strip()
                doc_id = line.split(":", 1)[1].strip("=").strip()
                buf = []
            else:
                buf.append(line)
    if doc_id is not None:
        docs[doc_id] = "\n".join(buf).strip()
    return docs

def load_references(path_txt: str) -> Dict[str, str]:
    refs, doc_id, buf = {}, None, []
    with open(path_txt, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("===DOC_ID:"):
                if doc_id is not None:
                    refs[doc_id] = "\n".join(buf).strip()
                doc_id = line.split(":", 1)[1].strip("=").strip()
                buf = []
            else:
                buf.append(line)
    if doc_id is not None:
        refs[doc_id] = "\n".join(buf).strip()
    return refs

async def call_api(client: httpx.AsyncClient, text: str, modo: int, doc_id: str) -> str:
    payload = {"docs": {doc_id: text}, "modo": modo, "sintesi_aggregata": 0}
    r = await client.post(API_URL, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    # Your API returns {"summaries": {...}} (or a string when aggregated).
    if isinstance(data["summaries"], dict):
        return data["summaries"][doc_id]
    return data["summaries"]

async def run_eval(long_txt: str, ref_txt: str, outdir: str, modo: int = DEFAULT_MODO):
    os.makedirs(outdir, exist_ok=True)
    docs = load_long_texts(long_txt)
    refs = load_references(ref_txt)

    rows = []
    async with httpx.AsyncClient() as client:
        for doc_id in tqdm(sorted(docs.keys())):
            original = docs[doc_id]
            reference = refs.get(doc_id, original)  # fallback if any mismatch
            try:
                t0 = time.perf_counter()
                summary = await call_api(client, original, modo, doc_id)
                latency_sec = time.perf_counter() - t0

                lm = M.length_metrics(original, summary, modo)
                rm = M.rouge_metrics(reference, summary)
                bm = M.bertscore_metrics(reference, summary)
                rd = M.readability_metrics(summary)
                ec = M.entity_consistency(original, summary)

                row = {"doc_id": doc_id, "latency_sec": latency_sec}
                row.update(lm); row.update(rm); row.update(bm); row.update(rd); row.update(ec)
                rows.append(row)
            except Exception as e:
                rows.append({"doc_id": doc_id, "error": str(e)})

    df = pd.DataFrame(rows)
    per_doc_csv = os.path.join(outdir, "per_doc.csv")
    df.to_csv(per_doc_csv, index=False, encoding="utf-8")
    print(f"Saved per-doc metrics -> {per_doc_csv}")

    # summary stats over numeric cols (excluding errors)
    if "error" in df.columns:
        ok = df[df["error"].isna()].select_dtypes("number") if df["error"].notna().any() else df.select_dtypes("number")
    else:
        ok = df.select_dtypes("number")

    means = ok.mean(numeric_only=True).to_dict()
    stds  = ok.std(numeric_only=True).to_dict()
    summary = {"means": means, "stds": stds, "docs_evaluated": int(len(ok))}
    with open(os.path.join(outdir, "summary_report.json"), "w", encoding="utf-8") as w:
        json.dump(summary, w, indent=2, ensure_ascii=False)
    print("Saved summary_report.json")

def main():
    import argparse, datetime
    parser = argparse.ArgumentParser(description="Evaluate summarization metrics over a corpus.")
    parser.add_argument("--long_texts", default="long_texts.txt")
    parser.add_argument("--references", default="reference_summaries.txt")
    parser.add_argument("--modo", type=int, default=DEFAULT_MODO)
    parser.add_argument("--outdir", default=None)
    args = parser.parse_args()

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    outdir = args.outdir or f"results/run_{stamp}"

    asyncio.run(run_eval(args.long_texts, args.references, outdir, args.modo))

if __name__ == "__main__":
    main()
