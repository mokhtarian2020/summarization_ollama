from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from typing import Dict, List

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"  # OpenAI-compatible chat endpoint
MODEL_NAME = "llama3.2"  # Adjust if needed
MAX_TOKENS = 128000  # LLaMA 3.2 context window
TOKEN_PER_WORD = 1.3
MAX_WORDS = int(MAX_TOKENS / TOKEN_PER_WORD)

class SummarizeRequest(BaseModel):
    docs: Dict[str, str]
    modo: int  # e.g., 10 for 10% summary

def split_text_into_chunks(text: str, max_words: int = 1000) -> List[str]:
    words = text.split()
    return [' '.join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

def build_system_prompt(doc_id: str, modo: int, original_word_count: int) -> str:
    target_words = max(1, int(original_word_count * modo / 100))
    return f"""
Sei un professionista esperto nel riassunto di testi complessi. Il tuo compito è produrre riassunti in italiano corretti, chiari e sostanzialmente più brevi rispetto al testo originale.

📌 Obiettivo:
- Riassumi il contenuto del documento identificato come '{doc_id}' riducendolo al {modo}% della sua lunghezza originale.
- Il riassunto non deve superare circa {target_words} parole.
- Mantieni solo le informazioni essenziali.
- Evita dettagli superflui, esempi, ripetizioni o ricostruzioni creative.

🎯 Stile e formato:
- Usa un tono formale e conciso.
- Scrivi in un solo paragrafo coeso.
- Il riassunto deve concludersi in modo completo e logico, senza frasi interrotte o finali lasciati in sospeso.
- Non usare la prima persona.
- Non dire “ecco il riassunto” o “come richiesto”.
- Non fare domande né menzionare la tua identità o ruolo.
"""

async def summarize_text_chunk(text: str, modo: int, doc_id: str, total_words: int) -> str:
    user_instruction = (
        f"Fornisci un riassunto chiaro, sintetico e completo del seguente testo. "
        f"Il riassunto deve essere ridotto a circa il {modo}% della lunghezza originale, ovvero non più di {int(total_words * modo / 100)} parole. "
        f"Il riassunto deve terminare con una conclusione chiara e completa.\n\n{text}"
    )

    messages = [
        {"role": "system", "content": build_system_prompt(doc_id, modo, total_words)},
        {"role": "user", "content": user_instruction}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(OLLAMA_URL, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Ollama failed to summarize {doc_id}")

    result = response.json()
    return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

@app.post("/summarize")
async def summarize_documents(request: SummarizeRequest):
    if request.modo <= 0 or request.modo >= 100:
        raise HTTPException(status_code=400, detail="Modo must be between 1 and 99.")

    summaries = {}
    for doc_id, text in request.docs.items():
        text = text.strip()
        word_count = len(text.split())
        estimated_tokens = int(word_count * TOKEN_PER_WORD)

        if word_count <= MAX_WORDS:
            summary = await summarize_text_chunk(text, request.modo, doc_id, word_count)
        else:
            chunks = split_text_into_chunks(text, max_words=1000)
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summary = await summarize_text_chunk(chunk, request.modo, f"{doc_id}-part{i+1}", len(chunk.split()))
                chunk_summaries.append(chunk_summary)

            merged_summary_text = " ".join(chunk_summaries)
            summary = await summarize_text_chunk(merged_summary_text, request.modo, f"{doc_id}-final", len(merged_summary_text.split()))

        summaries[doc_id] = summary

    return {"summaries": summaries}
