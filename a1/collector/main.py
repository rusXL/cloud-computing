from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from typing import Dict, Any
import httpx
from contextlib import asynccontextmanager
import os


CAMERA = os.getenv("CAMERA_URL", "http://camera")
COLLECTOR = os.getenv("COLLECTOR_URL", "http://collector")
IMAGE_ANALYSIS = os.getenv("IMAGE_ANALYSIS_URL", "http://image-analysis")
FACE_RECOGNITION = os.getenv("FACE_RECOGNITION_URL", "http://face-recognition")
SECTION = os.getenv("SECTION_URL", "http://section")
ALERT = os.getenv("ALERT_URL", "http://alert")


http_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await http_client.aclose()


app = FastAPI(title="Collector Service", lifespan=lifespan)


# send and forget
async def forward_request(
    url: str,
    payload: Dict[str, Any],
    service_name: str,
):
    """Forward payload to remote service."""
    try:
        response = await http_client.post(url, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] HTTP to {service_name}: {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"[ERROR] Request to {service_name}: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected to {service_name}: {e}")


# image analysis -> section
async def image_analysis(payload: Dict[str, Any]):
    """Image Analysis -> Section flow."""
    await forward_request(
        f"{IMAGE_ANALYSIS}/frame",
        {**payload, "destination": f"{COLLECTOR}/persons"},
        "Image Analysis",
    )


@app.api_route("/persons", methods=["POST"])
async def persons(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    persons = payload.get("persons", [])
    if persons:
        background_tasks.add_task(
            forward_request, f"{SECTION}/persons", payload, "Section"
        )
    return "Accepted"


# face recognition -> alert
async def face_recognition(payload: Dict[str, Any]):
    """Face Recognition -> Alert flow."""
    await forward_request(
        f"{FACE_RECOGNITION}/frame",
        {**payload, "destination": f"{COLLECTOR}/known-persons"},
        "Face Recognition",
    )


@app.api_route("/known-persons", methods=["POST"])
async def known_persons(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    known_persons = payload.get("known-persons", [])
    if known_persons:
        background_tasks.add_task(forward_request, f"{ALERT}/alerts", payload, "Alert")
    return "Accepted"


# receive frame from camera
@app.post("/frame")
async def frame(request: Request, background_tasks: BackgroundTasks):
    """Receives a frame and immediately returns; processes flows in background."""
    payload = await request.json()

    # Schedule flows as separate background tasks
    background_tasks.add_task(image_analysis, payload)
    background_tasks.add_task(face_recognition, payload)

    return "Accepted"


# probes
@app.get("/livenessProbe")
async def liveness_probe():
    return "Alive"


@app.get("/readinessProbe")
async def readiness_probe():
    if http_client is None or http_client.is_closed:
        raise HTTPException(status_code=503, detail="HTTP client not ready")
    return "Ready"
