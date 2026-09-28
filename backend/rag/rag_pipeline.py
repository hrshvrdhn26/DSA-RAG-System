import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from groq import Groq
import json
from pydantic import BaseModel
from typing import List

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

print("Connected to Qdrant Cloud!")

COLLECTION_NAME = "transcription"
EMBEDDING_SIZE = 384

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model ready!")

def search(query, top_k=3):
    query_embedding = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=top_k,
        with_payload=True
    ).points

    return results

groq_client = Groq(
    api_key=GROQ_API_KEY
)

class Source(BaseModel):
    video_title: str
    start: float
    end: float
    youtube_url: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[Source]

SYSTEM_PROMPT = """
## ROLE
You are a DSA Video Knowledge Assistant.

## TASK
Answer the user's question using ONLY the retrieved transcript context.

## CONSTRAINTS
- Use only the provided context.
- Do not use outside knowledge.
- Do not invent or assume information.
- Do not fabricate timestamps, video titles, or URLs.
- If the context does not contain enough information to answer the question, use the fallback response.
- Keep the answer focused and technically clear.

## FALLBACK
If the context does not contain enough information, return:

"I couldn't find enough information about this in the provided DSA videos."

In this case, sources must be an empty list.

## OUTPUT FORMAT
Return ONLY valid JSON in this exact structure:

{
    "answer": "string",
    "sources": [
        {
            "video_title": "string",
            "start": 0,
            "end": 0,
            "youtube_url": "string"
        }
    ]
}

## ONE-SHOT EXAMPLE
Context:
Video Title: DSA Patterns Episode 7
Timestamp: 371 - 415
Text:
The two pointer technique uses two pointers to process elements from different positions of the array.

Question:
What is the two pointer technique?

Output:
{
    "answer": "The two pointer technique uses two pointers to process elements from different positions of the array.",
    "sources": [
        {
            "video_title": "DSA Patterns Episode 7",
            "start": 371,
            "end": 415,
            "youtube_url": "https://youtu.be/rM9EthMlXnw"
        }
    ]
}
"""

def build_context(results):
    context = []

    for i, result in enumerate(results, start=1):
        payload = result.payload

        context.append(
            f"""
SOURCE {i}
Video Title: {payload.get("video_title", "")}
Timestamp: {payload.get("start", "")} - {payload.get("end", "")}
YouTube URL: {payload.get("youtube_url", "")}

Transcript:
{payload.get("text", "")}
"""
        )

    return "\n".join(context)

def generate_answer(query, results):
    if not results:
        return RAGResponse(
            answer="I couldn't find enough information about this in the provided DSA videos.",
            sources=[]
        )

    context = build_context(results)

    user_prompt = f"""
## RETRIEVED CONTEXT
{context}

## USER QUESTION
{query}
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0
    )

    llm_output = response.choices[0].message.content

    try:
        data = json.loads(llm_output)
        validated_response = RAGResponse.model_validate(data)
        return validated_response
    except Exception as e:
        print("Invalid LLM response:")
        print(llm_output)
        print("Error:", e)
        return None

# query = input("Ask your DSA question: ")

def answer_question(query: str):
    results = search(
        query,
        top_k=5
    )

    results = results[:5]

    response = generate_answer(
        query,
        results
    )
    return response
    # return your final response

# if response:
#     print("\nANSWER:")
#     print(response.answer)

#     print("\nSOURCES:")

#     for source in response.sources:
#         print(f"\nVideo: {source.video_title}")
#         print(f"Timestamp: {source.start} - {source.end}")
#         print(f"URL: {source.youtube_url}")