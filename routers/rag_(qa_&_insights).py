import os
import json
from google.cloud import aiplatform
from google.cloud import storage
from vertexai.preview.language_models import TextGenerationModel
from services.project_utils import get_user_session_structure, get_gcs_paths, get_username_from_env

# Config
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
BUCKET = "your-gcs-bucket"
EMBED_MODEL = "publishers/google/models/textembedding-gecko@001"
GEMINI_MODEL = "gemini-1.5-pro-preview-0409"
RAW_DIR = "/data/processed"
TOP_N_CHUNKS = 5  # Number of text chunks to retrieve

# Initialize Vertex AI SDK
aiplatform.init(project=PROJECT_ID, location=LOCATION)
embed_model = aiplatform.TextEmbeddingModel(EMBED_MODEL)
gemini = TextGenerationModel.from_pretrained(model_name=GEMINI_MODEL)
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET)


def get_chunks_from_json(json_dir, user_session_id=None):
    """
    Get text chunks from JSON files in user session structure.
    
    Args:
        json_dir: Directory containing JSON files (legacy) or user session ID
        user_session_id: Optional user session ID for new structure
    """
    chunks = []
    
    # If user_session_id provided, use new structure
    if user_session_id:
        # Parse user_session_id to get parts for path resolution
        parts = user_session_id.split('-', 1)
        if len(parts) >= 2:
            username = parts[0]
            uid = parts[1]
            # Create dummy filename for structure resolution
            session_structure = get_user_session_structure("document.pdf", username, uid)
            json_dir = session_structure["pipeline"]
    
    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            with open(os.path.join(json_dir, filename), "r") as f:
                data = json.load(f)
                # Handle both old and new JSON structures
                text = data.get("content", "")
                if not text and "extracted_data" in data:
                    text = data["extracted_data"].get("text_content", "")
                
                for idx, paragraph in enumerate(text.split("\n\n")):
                    if paragraph.strip():
                        chunk_id = f"{filename}_c{idx:04d}"
                        chunks.append({"text": paragraph.strip(), "chunk_id": chunk_id})
    return chunks


def embed_chunks(chunks):
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_model.get_embeddings(instances=texts)
    for i, emb in enumerate(embeddings):
        chunks[i]["embedding"] = emb
    return chunks


def upload_embeddings_to_gcs(chunks, filename, user_session_id=None, username=None):
    """
    Upload embeddings to GCS using new user session structure.
    
    Args:
        chunks: Text chunks with embeddings
        filename: Embedding filename
        user_session_id: User session identifier
        username: Username for path resolution
    """
    if username is None:
        username = get_username_from_env()
    
    if user_session_id is None:
        user_session_id = f"{username}-default"
    
    # Get user session structure for local storage
    session_structure = get_user_session_structure("embeddings.jsonl", username)
    local_path = session_structure["metadata"] / filename
    
    # Save locally first
    with open(local_path, "w") as f:
        for chunk in chunks:
            json_obj = {
                "id": chunk["chunk_id"],
                "text": chunk["text"],
                "embedding": chunk["embedding"],
            }
            f.write(json.dumps(json_obj) + "\n")
    
    # Upload to GCS using new path structure
    gcs_paths = get_gcs_paths(BUCKET, user_session_id)
    blob = bucket.blob(f"{user_session_id}/embeddings/{filename}")
    blob.upload_from_filename(local_path)
    gcs_uri = f"{gcs_paths['embeddings']}/{filename}"
    return gcs_uri


def create_vertex_ai_index(gcs_uri, dim):
    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name="legal-docs-index",
        contents_delta_uri=gcs_uri,
        dimensions=dim,
        approximate_neighbors_count=10,
    )
    index.wait()
    index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(display_name="legal-docs-endpoint")
    deployed_index = index_endpoint.deploy_index(index=index)
    # Return endpoint client for queries
    return index_endpoint, deployed_index


def retrieve_top_chunks(index_endpoint, deployed_index, chunks, query, top_k=TOP_N_CHUNKS):
    query_emb = embed_model.get_embeddings(instances=[query])[0]
    response = index_endpoint.find_neighbors(
        deployed_index_id=deployed_index.id,
        queries=[query_emb],
        num_neighbors=top_k,
    )
    results = []
    for match in response[0]:
        # match.id corresponds to chunk index in this example
        matched_chunk = next(c for c in chunks if c["chunk_id"] == match.id)
        results.append(matched_chunk)
    return results


def prepare_rag_prompt_QA(chunks, user_query):
    # Build numbered context items with chunk text and IDs
    context_items = []
    for i, chunk in enumerate(chunks, start=1):
        ctxt = f"Context {i}: {chunk['text']} (doc:{chunk['chunk_id']})"
        context_items.append(ctxt)
    context_str = "\n".join(context_items)

    qa_prompt = (
        "You are a legal assistant. Use ONLY the following numbered context items to answer the question. "
        "If the law is not present in the context, say \"not found in documents\".\n\n"
        f"{context_str}\n\n"
        f"Question: {user_query}\n"
        "Answer (concise, cite chunks as [doc:chunk]):"
    )
    return qa_prompt


def prepare_rag_prompt_risk_insights(chunks):
    context_items = []
    for chunk in chunks:
        context_items.append(f"{chunk['chunk_id']}: {chunk['text']}")
    context_str = "\n\n".join(context_items)

    risk_prompt = (
        "You are a legal risk evaluator. For each provided clause, return JSON array of objects:\n"
        '{ "chunk_id": "...", "risk_level": "High|Medium|Low|None", "reason": "...", "suggested_text": "..." }\n\n'
        f"Clauses:\n{context_str}\n"
    )
    return risk_prompt


def generate_answer(prompt):
    response = gemini.predict(prompt)
    return response.text


def main():
    # Load and embed chunks
    username = get_username_from_env()
    user_session_id = f"{username}-default"  # Can be passed as parameter
    
    chunks = get_chunks_from_json(RAW_DIR, user_session_id)
    print(f"Loaded {len(chunks)} text chunks from preprocessed data.")

    chunks = embed_chunks(chunks)
    print("Generated embeddings for all chunks.")

    # Save embeddings to GCS and create index
    gcs_uri = upload_embeddings_to_gcs(chunks, "legal_chunks_embeddings.jsonl", user_session_id, username)
    print(f"Uploaded embeddings to GCS: {gcs_uri}")

    index_endpoint, deployed_index = create_vertex_ai_index(gcs_uri, dim=len(chunks[0]["embedding"]))
    print("Created and deployed Vertex AI Matching Engine index.")

    # Example User Q&A Flow
    user_question = "What is the termination notice period for contractor?"
    top_chunks = retrieve_top_chunks(index_endpoint, deployed_index, chunks, user_question)
    print(f"Retrieved {len(top_chunks)} chunks for the question.")

    # Prepare Q&A prompt with system and user prompt structure
    qa_prompt = prepare_rag_prompt_QA(top_chunks, user_question)
    qa_answer = generate_answer(qa_prompt)
    print("\nQ&A Bot Result:\n", qa_answer)

    # Prepare Risk Insights prompt and get structured JSON output
    risk_prompt = prepare_rag_prompt_risk_insights(top_chunks)
    risk_insights = generate_answer(risk_prompt)
    print("\nRisk Insight JSON:\n", risk_insights)


if __name__ == "__main__":
    main()
