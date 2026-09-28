from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.rag_pipeline import answer_question

app = FastAPI(
    title="DSA RAG API",
    description="AI-powered DSA Video Knowledge Retrieval API",
    version="1.0.0"
)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)


@app.get("/")
def root():
    return {
        "message": "DSA RAG API is running",
        "status": "ok"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        return answer_question(request.question)

    except Exception as error:
        print(f"RAG ERROR: {error}")

        raise HTTPException(
            status_code=500,
            detail="Error while processing the question"
        )