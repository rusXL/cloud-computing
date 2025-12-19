"""
Bucket FastAPI Application

Each bucket stores key-value pairs in memory and persists to JSON on disk.
Runs as a separate container with BUCKET_ID environment variable.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response

logger = logging.getLogger("uvicorn")

# config - extract bucket ID from pod name (e.g., "bucket-0" -> 0)
POD_NAME = os.environ.get("POD_NAME", "bucket-0")
BUCKET_ID = int(POD_NAME.split("-")[-1])
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / f"bucket_{BUCKET_ID}.json"


def load_data() -> dict[str, str]:
    """Load data from JSON file on startup."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Bucket {BUCKET_ID}: Loaded {len(data)} keys from {DATA_FILE}")
            return data
        except Exception as e:
            logger.error(f"Bucket {BUCKET_ID}: Error loading data: {e}")
            return {}
    else:
        logger.info(f"Bucket {BUCKET_ID}: No existing data file, starting fresh")
        return {}


def save_data(storage: dict[str, str]):
    """Persist data to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(storage, f, ensure_ascii=False, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    app.state.storage = load_data()
    yield


app = FastAPI(lifespan=lifespan)


@app.put("/put")
async def put(request: Request, key: str, value: str):
    storage = request.app.state.storage
    action = "updated" if key in storage else "created"
    
    storage[key] = value
    save_data(storage)
    
    return {"key": key, "value": storage[key], "action": action}

@app.get("/get/{key:path}")
async def get(request: Request, key: str):
    storage = request.app.state.storage
    if key not in storage:
        raise HTTPException(status_code=404, detail=f"Key not found: {key} in bucket: {BUCKET_ID}")
    return {"value": storage[key]}

@app.delete("/delete/{key:path}")
async def delete(request: Request, key: str):
    storage = request.app.state.storage
    if key not in storage:
        raise HTTPException(status_code=404, detail=f"Key not found: {key} in bucket: {BUCKET_ID}")
    value = storage[key]
    del storage[key]
    save_data(storage)

    return {"key": key, "value": value}


@app.get("/health")
async def health(request: Request):
    return {"bucket_id": BUCKET_ID, "keys_len": len(request.app.state.storage)}

