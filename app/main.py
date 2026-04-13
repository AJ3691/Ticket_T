import json
import logging
import time
import uuid
from fastapi import FastAPI, Request
from app.engine import get_recommendations
from app.models import TicketInput, TriageResponse
from app.rules.llm import get_llm_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket_triage")

_metrics: dict[str, int | float] = {
    "request_count": 0,
    "error_count": 0,
    "total_latency_ms": 0.0,
}

app = FastAPI(
    title="Support Ticket Triage",
    description="Returns ranked recommendations for incoming support tickets.",
    version="0.1.0",
)

@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
    except Exception as e:
        raise e
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        _metrics["request_count"] += 1
        _metrics["total_latency_ms"] += elapsed_ms
        if status_code >= 400:
            _metrics["error_count"] += 1
        logger.info(json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "latency_ms": round(elapsed_ms, 2),
        }))

    return response

@app.post("/recommendations", response_model=TriageResponse)
def recommend(ticket: TicketInput) -> TriageResponse:
    result = get_recommendations(title=ticket.title, description=ticket.description, top_n=ticket.top_n)
    return TriageResponse(recommendations=result)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return {**_metrics, **get_llm_metrics()}
