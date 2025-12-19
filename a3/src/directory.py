"""
Directory FastAPI Application (Router)

Routes requests to bucket containers using hashing.
The client interacts only with this service; buckets are internal.
"""

import hashlib
import os
from contextlib import asynccontextmanager
from typing import Optional
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# config
BUCKET_COUNT = int(os.environ.get("BUCKET_COUNT", "2"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared HTTP client lifecycle."""
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)


def stable_hash(key: str) -> int:
    """Deterministic hash function for routing keys to buckets."""
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)


def get_bucket_url(key: str) -> tuple[str, int, int]:
    """Determine which bucket should handle this key."""
    digest = stable_hash(key)
    bucket_id = digest % BUCKET_COUNT
    return f"http://bucket-{bucket_id}.bucket:8000", bucket_id, digest

from fastapi import Request, HTTPException
import httpx

async def forward_to_bucket(client: httpx.AsyncClient, key: str, method: str, params: dict = None):
    """
    Forward a request to the appropriate bucket.
    client: async http client
    key: entry key
    method: 'GET', 'PUT', 'DELETE'
    params?: payload for PUT requests
    """
    bucket_url, bucket_id, digest = get_bucket_url(key)

    try:
        if method.upper() == "GET":
            resp = await client.get(f"{bucket_url}/get/{key}")
        elif method.upper() == "PUT":
            resp = await client.put(f"{bucket_url}/put", params=params)
        elif method.upper() == "DELETE":
            resp = await client.delete(f"{bucket_url}/delete/{key}")
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        resp.raise_for_status()
        return {**resp.json(), "bucket_id": bucket_id, "digest": str(digest)[-1:]}

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Bucket unavailable: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)


@app.put("/put")
async def put(request: Request, key: str, value: str):
    """Upsert a key-value pair."""
    return await forward_to_bucket(request.app.state.http_client, key, "PUT", params={"key": key, "value": value})

@app.get("/get/{key:path}")
async def get(request: Request, key: str):
    """Get value by key. Returns None if entry with a key does not exist."""
    return await forward_to_bucket(request.app.state.http_client, key, "GET")

@app.delete("/delete/{key:path}")
async def delete(request: Request, key: str):
    """Delete a key. Throws if entry with a key does not exist."""
    return await forward_to_bucket(request.app.state.http_client, key, "DELETE")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"bucket_count": BUCKET_COUNT}

