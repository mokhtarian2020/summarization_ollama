from fastapi import HTTPException
from config import MAX_WORDS, TOKEN_PER_WORD, REQUEST_TIMEOUT_SECONDS
from utils.chunking import split_text_into_chunks
from utils.prompts import build_system_prompt
from ollama import chat
import signal

MODEL_NAME = "llama3.1"

def _enforce_length(summary: str, target_words: int) -> str:
    """Hard cap the length without awkward truncation:
    1) try sentence-wise packing up to target_words
    2) fallback to word trim
    """
    words = summary.strip().split()
    if len(words) <= target_words:
        return summary.strip() if summary.strip().endswith(('.', '!', '?')) else summary.strip() + "."
    # sentence-wise packing
    sentences = summary.strip().replace("\n", " ").split(". ")
    packed, count = [], 0
    for s in sentences:
        w = s.split()
        if count + len(w) > target_words:
            break
        packed.append(s.rstrip("."))
        count += len(w)
    if packed:
        out = ". ".join(packed).strip()
        return out if out.endswith(('.', '!', '?')) else out + "."
    # fallback: word trim
    trimmed = " ".join(words[:target_words]).rstrip()
    return trimmed if trimmed.endswith(('.', '!', '?')) else trimmed + "."

def summarize_text_chunk(text: str, modo: int, doc_id: str, total_words: int) -> str:
    target_words = max(1, int(total_words * modo / 100))

    # User instruction: balanced (faithful + concise) and explicit hard limit
    user_instruction = (
        "Fornisci un riassunto fedele, chiaro e conciso del seguente testo.\n"
        f"- Obiettivo di lunghezza: circa il {modo}% (≈ {target_words} parole). **Non superare questo limite**.\n"
        "- Mantieni solo le informazioni essenziali, le relazioni causali e le conclusioni principali.\n"
        "- NON introdurre contenuti non presenti; NON generalizzare; NON omettere numeri, date, nomi, luoghi o unità rilevanti.\n"
        "- Quando utile alla chiarezza, conserva brevi parole chiave o segmenti testuali originali.\n\n"
        "TESTO:\n"
        f"{text}"
    )

    messages = [
        {"role": "system", "content": build_system_prompt(doc_id, modo, total_words)},
        {"role": "user", "content": user_instruction}
    ]

    def handler(signum, frame):
        raise TimeoutError("Summarization timed out")

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(REQUEST_TIMEOUT_SECONDS)

    try:
        result = chat(model=MODEL_NAME, messages=messages)
        signal.alarm(0)
    except TimeoutError:
        raise HTTPException(status_code=504, detail=f"Ollama timed out while summarizing '{doc_id}'")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama error for '{doc_id}': {str(e)}")

    raw = result['message']['content'].strip()
    # Enforce the target length post-generation to reduce deviation sharply
    return _enforce_length(raw, target_words)

async def summarize_documents_handler(request):
    if request.modo <= 0 or request.modo >= 100:
        raise HTTPException(status_code=400, detail="Modo must be between 1 and 99.")

    # Aggregated synthesis
    if getattr(request, "sintesi_aggregata", 0) == 1:
        all_text = " ".join(text.strip() for text in request.docs.values())
        word_count = len(all_text.split())

        if word_count <= MAX_WORDS:
            summary = summarize_text_chunk(all_text, request.modo, "aggregated", word_count)
        else:
            chunks = split_text_into_chunks(all_text, max_words=1000)
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary = summarize_text_chunk(
                    chunk, request.modo, f"aggregated-part{i+1}", len(chunk.split())
                )
                chunk_summaries.append(chunk_summary)

            merged_summary_text = " ".join(chunk_summaries)
            summary = summarize_text_chunk(
                merged_summary_text, request.modo, "aggregated-final", len(merged_summary_text.split())
            )

        return {"summaries": summary}

    # Default: per-document summaries
    summaries = {}
    for doc_id, text in request.docs.items():
        text = text.strip()
        word_count = len(text.split())

        if word_count <= MAX_WORDS:
            summary = summarize_text_chunk(text, request.modo, doc_id, word_count)
        else:
            chunks = split_text_into_chunks(text, max_words=1000)
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary = summarize_text_chunk(
                    chunk, request.modo, f"{doc_id}-part{i+1}", len(chunk.split())
                )
                chunk_summaries.append(chunk_summary)

            merged_summary_text = " ".join(chunk_summaries)
            summary = summarize_text_chunk(
                merged_summary_text, request.modo, f"{doc_id}-final", len(merged_summary_text.split())
            )

        summaries[doc_id] = summary

    return {"summaries": summaries}
