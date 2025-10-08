from fastapi import FastAPI
from models import SummarizeRequest
from services.summarize import summarize_documents_handler

app = FastAPI()

@app.post("/summarize")
async def summarize_documents(request: SummarizeRequest):
    return await summarize_documents_handler(request)