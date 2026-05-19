# metrics/compare_runs.py
import os, json, pandas as pd

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(run_a: str, run_b: str):
    A = load(os.path.join(run_a, "summary_report.json"))
    B = load(os.path.join(run_b, "summary_report.json"))
    keys = sorted(set(A["means"].keys()) | set(B["means"].keys()))
    rows = []
    for k in keys:
        a = A["means"].get(k)
        b = B["means"].get(k)
        if a is None or b is None:
            continue
        delta = (b - a)
        pct = (delta / a * 100.0) if a else None
        rows.append({"metric": k, "run_a": a, "run_b": b, "delta": delta, "delta_pct": pct})
    df = pd.DataFrame(rows).sort_values("metric")
    print(df.to_string(index=False))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("run_a")
    p.add_argument("run_b")
    args = p.parse_args()
    main(args.run_a, args.run_b)
