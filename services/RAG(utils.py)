import os
import json
from google.cloud import storage
from google.cloud import aiplatform

def get_chunks_from_json(json_dir):
    chunks = []
    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            with open(os.path.join(json_dir, filename), "r") as f:
                data = json.load(f)
                text = data.get("content", "")
                for idx, paragraph in enumerate(text.split("\n\n")):
                    if paragraph.strip():
                        chunk_id = f"{filename}_c{idx:04d}"
                        chunks.append({"text": paragraph.strip(), "chunk_id": chunk_id})
    return chunks

def embed_chunks(chunks, embed_model):
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_model.get_embeddings(instances=texts)
    for i, emb in enumerate(embeddings):
        chunks[i]["embedding"] = emb
    return chunks

def upload_embeddings_to_gcs(chunks, filename, bucket_name):
    local_path = filename
    with open(local_path, "w") as f:
        for chunk in chunks:
            json_obj = {
                "id": chunk["chunk_id"],
                "text": chunk["text"],
                "embedding": chunk["embedding"],
            }
            f.write(json.dumps(json_obj) + "\n")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"embeddings/{filename}")
    blob.upload_from_filename(local_path)
    gcs_uri = f"gs://{bucket_name}/embeddings/{filename}"
    return gcs_uri
