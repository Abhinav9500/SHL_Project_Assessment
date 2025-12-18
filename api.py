import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

# Import your existing search logic
from vector_engine import collection, get_recommendations

app = FastAPI(title="SHL Assessment Recommender API")

# --- PDF Requirement: Models for JSON Validation ---
class QueryRequest(BaseModel):
    query: str

class AssessmentResponse(BaseModel):
    url: str
    name: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]

class RecommendationResponse(BaseModel):
    recommended_assessments: List[AssessmentResponse]

# --- 1. Health Check Endpoint [cite: 155, 161] ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# --- 2. Recommendation Endpoint [cite: 163, 167] ---
@app.post("/recommend", response_model=RecommendationResponse)
async def recommend(request: QueryRequest):
    try:
        # Perform vector search (requesting top 10 as per PDF) [cite: 163]
        results = collection.query(
            query_texts=[request.query],
            n_results=10
        )
        
        if not results['metadatas'] or not results['metadatas'][0]:
            return {"recommended_assessments": []}

        formatted_results = []
        for item in results['metadatas'][0]:
            # Convert the stored JSON string back into a Python List
            t_type = json.loads(item['test_type']) if isinstance(item['test_type'], str) else item['test_type']
            
            formatted_results.append({
                "url": item['url'],
                "name": item['name'],
                "adaptive_support": item['adaptive_support'],
                "description": item['description'],
                "duration": int(item['duration']),
                "remote_support": item['remote_support'],
                "test_type": t_type
            })

        return {"recommended_assessments": formatted_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)