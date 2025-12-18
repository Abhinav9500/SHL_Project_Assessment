import os
import json
import glob
import google.generativeai as genai
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

DATA_FOLDER = "data/assessments_raw"
COLLECTION_NAME = "shl_assessments"

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.model_name = 'models/text-embedding-004'
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            try:
                response = genai.embed_content(model=self.model_name, content=text, task_type="retrieval_document")
                embeddings.append(response['embedding'])
            except Exception as e:
                embeddings.append([0] * 768) 
        return embeddings

chroma_client = chromadb.PersistentClient(path="data/chroma_db")
embedding_function = GeminiEmbeddingFunction()
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=embedding_function)

def ingest_data():
    json_files = glob.glob(os.path.join(DATA_FOLDER, "*.json"))
    print(f"Found {len(json_files)} files. Starting ingestion...")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                item = json.load(f)
            
            doc_id = os.path.basename(file_path).replace(".json", "")
            # Create a rich text representation for search
            text_content = f"Name: {item['name']}. Type: {', '.join(item['test_type'])}. Description: {item['description']}"
            
            collection.upsert(
                ids=[doc_id],
                documents=[text_content],
                metadatas=[{
                    "url": item['url'],
                    "name": item['name'],
                    "adaptive_support": item['adaptive_support'],
                    "description": item['description'],
                    "duration": item['duration'] if item['duration'] else 0,
                    "remote_support": item['remote_support'],
                    "test_type": json.dumps(item['test_type'])
                }]
            )
        except Exception as e:
            print(f"Error ingesting {file_path}: {e}")

    print("Ingestion complete.")

def get_recommendations(query, n_results=5):
    """
    Returns a natural language explanation (for Streamlit UI)
    and retrieved metadata.
    """
    print(f"\nSearching for: '{query}'")
    
    # 1. Query the vector database
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    if not results['metadatas'] or not results['metadatas'][0]:
        return "No relevant assessments found."

    retrieved_items = results['metadatas'][0]
    
    # 2. Build context for the LLM
    # We include duration and name to give the AI enough info to explain its choice
    context_text = "\n".join([f"- {item['name']} (Duration: {item['duration']} mins)" for item in retrieved_items])

    prompt = f"""
    You are an expert HR assistant. A user is looking for an assessment test.
    User Query: "{query}"
    
    Best Matches found in our SHL catalog:
    {context_text}
    
    Please explain briefly and professionally why these specific assessments are good matches for the user's requirements.
    """

    ai_response = "AI explanation currently unavailable."

    # 3. Smart Model Selector (PDF Requirement: Modern LLM-based techniques)
    # Using the models verified in your environment earlier
    model_candidates = [
        'models/gemini-2.5-flash', 
        'models/gemini-2.0-flash', 
        'models/gemini-1.5-flash', 
        'gemini-pro'
    ]

    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            ai_response = response.text
            break 
        except Exception:
            continue 
    
    return ai_response

if __name__ == "__main__":
    ingest_data()