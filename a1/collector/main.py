from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from typing import Dict, Any
import asyncio
import httpx
from models import Frame
from contextlib import asynccontextmanager
import os


image_analysis_lock = asyncio.Lock()
face_recognition_lock = asyncio.Lock()
section_lock = asyncio.Lock()
alert_lock = asyncio.Lock()
failed_requests_lock = asyncio.Lock()

CAMERA = os.getenv("CAMERA_URL", "http://camera")
IMAGE_ANALYSIS = os.getenv("IMAGE_ANALYSIS_URL", "http://image-analysis")
FACE_RECOGNITION = os.getenv("FACE_RECOGNITION_URL", "http://face-recognition")
SECTION = os.getenv("SECTION_URL", "http://section")
ALERT = os.getenv("ALERT_URL", "http://alert")


http_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await http_client.aclose()


app = FastAPI(title="Collector Service", lifespan=lifespan)


async def forward_request(
    url: str,
    payload: Dict[str, Any],
    lock: asyncio.Lock,
    service_name: str,
    method: str = "POST",
) -> httpx.Response | None:
    """Send a payload to a service with retry and concurrency control."""
    async with lock:
        try:
            if method.upper() == "GET":
                response = await http_client.get(url)
                response.raise_for_status()
                return response
            elif method.upper() == "POST":
                response = await http_client.post(url, json=payload)
                response.raise_for_status()
                return response
        except httpx.RequestError as e:
            print(f"Request error to {service_name}: {e}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error to {service_name}: {e.response.status_code}")

    return None


# --- Separate flow tasks ---
async def image_analysis_flow(frame_payload: Dict[str, Any]):
    """Image Analysis -> Section flow."""
    image_resp = await forward_request(
        f"{IMAGE_ANALYSIS}/frame",
        frame_payload,
        image_analysis_lock,
        "Image Analysis",
    )
    if image_resp:
        persons_data = image_resp.json()
        await forward_request(
            f"{SECTION}/persons", persons_data, section_lock, "Section"
        )


async def face_recognition_flow(frame_payload: Dict[str, Any]):
    """Face Recognition -> Alert flow."""
    face_resp = await forward_request(
        f"{FACE_RECOGNITION}/frame",
        frame_payload,
        face_recognition_lock,
        "Face Recognition",
    )
    if face_resp and face_resp.status_code == 200:
        known_persons_data = face_resp.json()
        await forward_request(
            f"{ALERT}/alerts", known_persons_data, alert_lock, "Alert"
        )


@app.post("/frame")
async def frame_endpoint(frame: Frame, background_tasks: BackgroundTasks):
    """Receives a frame and immediately returns; processes flows in background."""
    try:
        frame_payload = frame.model_dump(mode="json")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Frame")

    # Schedule flows as separate background tasks
    background_tasks.add_task(image_analysis_flow, frame_payload)
    background_tasks.add_task(face_recognition_flow, frame_payload)

    return {"status": "accepted"}


@app.get("/livenessProbe")
async def liveness_probe():
    return "OK"


@app.get("/readinessProbe")
async def readiness_probe():
    if http_client is None or http_client.is_closed:
        raise HTTPException(status_code=503, detail="HTTP client not ready")
    return {"status": "ready"}
