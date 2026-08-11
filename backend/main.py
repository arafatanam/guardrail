from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import time
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="GuardRail API", version="0.1.0")

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# ---------- Pydantic models ----------


class TestCase(BaseModel):
    category: str
    subcategory: Optional[str] = None
    prompt: str
    expected_failure_mode: Optional[str] = None
    severity: str = "low"
    tags: Optional[List[str]] = []
    metadata: Optional[dict] = {}


class RunRequest(BaseModel):
    target_model_id: str = "test-target"  # e.g., "gpt-3.5-turbo", "hf/mistral"
    target_endpoint: Optional[str] = None  # URL for API, or None for HF
    test_case_ids: Optional[List[str]] = None  # if empty, run all

# ---------- Helper functions ----------


async def call_target_model(prompt: str, target: str, endpoint: Optional[str] = None):
    """
    Placeholder: use HuggingFace Inference API or a dummy response.
    In later weeks you'll support many providers.
    """
    # For now, just return a dummy response so the pipeline works end-to-end.
    # You can replace this with a real API call after proving the flow.
    hf_token = os.getenv("HF_TOKEN")
    if endpoint and hf_token:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {hf_token}"},
                    json={"inputs": prompt},
                    timeout=30.0
                )
                resp.raise_for_status()
                data = resp.json()
                # HF text-generation models return a list of dicts
                return data[0]["generated_text"] if isinstance(data, list) else str(data)
            except Exception:
                pass  # fallback to dummy
    # Dummy response
    return f"Dummy response to: {prompt[:50]}..."

# ---------- Routes ----------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/test-cases")
async def create_test_cases(cases: List[TestCase]):
    inserted = []
    for case in cases:
        result = supabase.table("test_cases").insert(case.dict()).execute()
        inserted.append(result.data[0] if result.data else None)
    return {"inserted": len(inserted), "data": inserted}


@app.get("/test-cases")
async def list_test_cases():
    result = supabase.table("test_cases").select("*").execute()
    return result.data


@app.post("/runs")
async def start_run(request: RunRequest):
    # Create run record
    run = supabase.table("runs").insert({
        "target_model_id": request.target_model_id,
        "status": "running",
        "config": {"endpoint": request.target_endpoint}
    }).execute()
    run_id = run.data[0]["id"]

    # Fetch test cases (all or filtered)
    if request.test_case_ids:
        # Fetch specific test cases by IDs (Supabase .in_)
        pass  # Implement later
    else:
        cases = supabase.table("test_cases").select("*").execute().data

    # Execute each test case and store results
    results_list = []
    for case in cases:
        start_time = time.time()
        response = await call_target_model(case["prompt"], request.target_model_id, request.target_endpoint)
        latency = (time.time() - start_time) * 1000

        # For now, dummy scoring (all zeros)
        result = supabase.table("results").insert({
            "run_id": run_id,
            "test_case_id": case["id"],
            "response": response,
            "latency_ms": latency,
            "token_count": len(response.split()),  # rough estimate
            "rule_score": 0.0,
            "classifier_score": 0.0,
            "llm_judge_score": 0.0,
            "final_score": 0.0,
            "tier_used": "dummy"
        }).execute()
        results_list.append(result.data[0])

    # Mark run as completed
    supabase.table("runs").update(
        {"status": "completed", "completed_at": "now()"}).eq("id", run_id).execute()

    return {"run_id": run_id, "results_count": len(results_list)}
