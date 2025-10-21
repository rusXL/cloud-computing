from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from typing import Dict, Any
import asyncio
import httpx
from models import Frame
from contextlib import asynccontextmanager


image_analysis_lock = asyncio.Lock()
face_recognition_lock = asyncio.Lock()
section_lock = asyncio.Lock()
alert_lock = asyncio.Lock()
failed_requests_lock = asyncio.Lock()


IMAGE_ANALYSIS_URL = "http://image-analysis/frame"
FACE_RECOGNITION_URL = "http://face-recognition/frame"
SECTION_URL = "http://section/persons"
ALERT_URL = "http://alert/alerts"


http_client: httpx.AsyncClient
failed_requests_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    yield
    print("Failed requests: ", failed_requests_count)
    await http_client.aclose()


app = FastAPI(title="Collector Service", lifespan=lifespan)


async def forward_request(
    url: str,
    payload: Dict[str, Any],
    lock: asyncio.Lock,
    service_name: str,
    retries: int = 3,
    backoff: int = 10,
) -> httpx.Response | None:
    """Send a payload to a service with retry and concurrency control."""
    global failed_requests_count

    for attempt in range(1, retries + 1):
        async with lock:
            try:
                response = await http_client.post(url, json=payload)
                response.raise_for_status()
                return response
            except httpx.RequestError as e:
                print(f"Request error to {service_name}: {e}, attempt {attempt}")
            except httpx.HTTPStatusError as e:
                print(
                    f"HTTP error to {service_name}: {e.response.status_code}, attempt {attempt}"
                )

        if attempt < retries:
            await asyncio.sleep(backoff)

    async with failed_requests_lock:
        failed_requests_count += 1
    print(f"Failed to post to {service_name} after {retries} attempts")

    return None


# --- Separate flow tasks ---
async def image_analysis_flow(frame_payload: Dict[str, Any]):
    """Image Analysis -> Section flow."""
    image_resp = await forward_request(
        IMAGE_ANALYSIS_URL,
        frame_payload,
        image_analysis_lock,
        "Image Analysis",
    )
    if image_resp:
        persons_data = image_resp.json()
        await forward_request(SECTION_URL, persons_data, section_lock, "Section")


async def face_recognition_flow(frame_payload: Dict[str, Any]):
    """Face Recognition -> Alert flow."""
    face_resp = await forward_request(
        FACE_RECOGNITION_URL,
        frame_payload,
        face_recognition_lock,
        "Face Recognition",
    )
    if face_resp and face_resp.status_code == 200:
        known_persons_data = face_resp.json()
        await forward_request(ALERT_URL, known_persons_data, alert_lock, "Alert")


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


# collector is ready is all other services are ready
@app.get("/readinessProbe")
async def readiness_probe():
    return "OK"
