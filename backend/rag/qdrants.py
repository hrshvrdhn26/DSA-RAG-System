import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny, PayloadSchemaType
from sentence_transformers import SentenceTransformer
from groq import Groq
import json

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    timeout=120
)

print("Connected to Qdrant Cloud!")

COLLECTION_NAME = "transcription"
EMBEDDING_SIZE = 384


# Delete collection if it already exists
if client.collection_exists(COLLECTION_NAME):
    print(f"Deleting existing collection: {COLLECTION_NAME}")
    client.delete_collection(COLLECTION_NAME)


# Create collection
client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=EMBEDDING_SIZE,
        distance=Distance.COSINE,
    ),
)

print(f"Created collection: {COLLECTION_NAME}")
print(f"Vector size: {EMBEDDING_SIZE}")

try:

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="video_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    print("Created payload index: video_id")

except Exception:

    print("video_id payload index already exists")

with open("../data/transcript_chunks.json", "r", encoding="utf-8") as f:
    documents = json.load(f)

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print("Embedding model ready!")
texts = [document["text"] for document in documents]


embeddings = model.encode(texts,
    batch_size=32,
    show_progress_bar=True,
    normalize_embeddings=True)

print(f"Generated {len(embeddings)} embeddings")
print(f"Embedding size: {len(embeddings[0])}")

# Upload embeddings in batches
BATCH_SIZE = 100

for start in range(0, len(documents), BATCH_SIZE):
    end = min(start + BATCH_SIZE, len(documents))
    points = []

    for i in range(start, end):
        point = PointStruct(
            id=i + 1,
            vector=embeddings[i].tolist(),
            payload=documents[i]
        )

        points.append(point)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=False
    )