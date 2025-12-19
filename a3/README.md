# Cloud Storage System

A distributed key-value storage system using Kubernetes with hash-based routing, implementing a **memory-resident directory** with **M disk buckets**.

## Architecture Overview

```
┌──────────┐   HTTP    ┌───────────────┐   HTTP    ┌──────────────────────┐
│  Client  │ ────────→ │   Directory   │ ────────→ │  Bucket StatefulSet  │
│          │           │   (Router)    │           │  ┌─────────────────┐ │
│          │           │               │           │  │ bucket-0        │ │
└──────────┘           │ • Hash: SHA256│           │  │   └─ data.json  │ │
                       │ • Routes to   │           │  ├─────────────────┤ │
                       │   bucket-{id} │           │  │ bucket-1        │ │
                       │   .bucket     │           │  │   └─ data.json  │ │
                       └───────────────┘           │  └─────────────────┘ │
                                                   └──────────────────────┘
```

## Design Decisions

### Hash Function: SHA256 with Modulo

```python
def stable_hash(key: str) -> int:
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)

bucket_id = stable_hash(key) % BUCKET_COUNT
```

- **Uniform distribution**: Keys are evenly distributed across buckets regardless of input patterns
- **Deterministic**: Same key always routes to the same bucket
- **Collision-resistant**: Different keys rarely map to the same bucket

**Empirical behavior**: With 2 buckets and random keys, we observe ~50% distribution to each bucket. The modulo operation ensures `bucket_id` is always in range `[0, M-1]`.

### Memory-Resident Directory

The **Directory** service acts as the memory-resident directory D:

- Maintains the hash function and routing logic in memory
- Routes PUT/GET/DELETE requests to the appropriate bucket
- **Client is unaware of hash function** - clients only interact with the directory's REST API

### Disk Buckets with Separate Processes

Each bucket runs as a **separate Kubernetes pod** (separate process):

- Stores data in memory (Python dict) for fast access
- **Persists to disk** (`/data/bucket_{id}.json`) on every write
- Uses Kubernetes `PersistentVolumeClaim` for durable storage

### Cheap Data Access

The design enables "cheap" client access:

1. **Single entry point**: Clients only know the Directory service URL
2. **O(1) routing**: Hash computation + service lookup is constant time
3. **No client-side routing**: Client sends request, directory handles routing
4. **Connection pooling**: Directory uses shared HTTP client for bucket requests

### Dynamic Scaling (StatefulSet)

Using Kubernetes StatefulSet with headless service enables:

- **Predictable pod names**: `bucket-0`, `bucket-1`, `bucket-{N-1}`
- **Direct pod addressing**: `http://bucket-{id}.bucket:8000`
- **Dynamic scaling**: `kubectl scale statefulset bucket --replicas=N`

## Components

### Directory (`src/directory.py`)

- FastAPI application acting as the router
- Computes `bucket_id = SHA256(key) % M`
- Forwards requests to `http://bucket-{id}.bucket:8000`
- Uses httpx AsyncClient with connection pooling

### Bucket (`src/bucket.py`)

- FastAPI application for key-value storage
- In-memory dict backed by JSON file on disk
- Extracts bucket ID from pod name (e.g., "bucket-0" → 0)

### Client

- Directory pod has a `NodeIP` service ahead, so that the client can access it via `http://NodeIP:8000`
- The role of client is either curl or **and recommended** FastAPI docs page.
- After you deploy everything with `./deploy.sh`, and enable port forwarding with `./open.sh`, you can access the FastAPI docs page at `http://localhost:8888/docs`, and interact with the Directory API.

## Local Quick Start

Make sure you have Kubernetes cluster started. Follow `https://kubernetes.io/docs/tasks/tools/` if you need installation.

```bash
# Deploy to Kubernetes
./deploy.sh

# Access the API
./open.sh
# Open http://localhost:8888/docs
```

## Docker Commands (change rusXL user to your username)

```bash
# Build images
docker build -f Dockerfile.directory -t rusxl/cloud-storage-directory:latest .
docker build -f Dockerfile.bucket -t rusxl/cloud-storage-bucket:latest .

# Push to DockerHub
docker push rusxl/cloud-storage-directory:latest
docker push rusxl/cloud-storage-bucket:latest
```

## Directory API Endpoints

| Method | Path                     | Description  | Response                                                               |
| ------ | ------------------------ | ------------ | ---------------------------------------------------------------------- |
| PUT    | `/put?key=...&value=...` | Store/update | `{"key", "value", "action": "created/updated", "bucket_id", "digest"}` |
| GET    | `/get/{key}`             | Get by key   | `{"value", "bucket_id", "digest"}` or 404                              |
| DELETE | `/delete/{key}`          | Delete key   | `{"key", "value", "bucket_id", "digest"}` or 404                       |
| GET    | `/health`                | Health check | `{"bucket_count"}`                                                     |

## Scaling Buckets

```bash
# Scale to 4 buckets
kubectl scale statefulset bucket --replicas=4 -n cloud-storage
kubectl set env deployment/directory BUCKET_COUNT=4 -n cloud-storage
```

> ⚠️ **Warning:** Scaling down may cause data loss for keys hashed to removed buckets.
