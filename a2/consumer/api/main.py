from enum import Enum
from fastapi import FastAPI
from fastapi import HTTPException
from shared.mongo import get_collection_by_type, get_client, get_db
from contextlib import asynccontextmanager
from pymongo.database import Database


class ImageType(str, Enum):
    potato = "potato"
    tomato = "tomato"
    pepper = "pepper"


# Global DB client
db: Database = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db

    client = get_client()
    db = get_db(client)

    yield

    client.close()


app = FastAPI(lifespan=lifespan)


# Probes (will hang in case something bad happened)
@app.get("/ready")
async def readiness():
    return "ready"


@app.get("/live")
async def liveness():
    return "alive"


# endpoints
@app.get("/image-plant/{image_type}/total")
def get_total_images(image_type: ImageType):
    collection = get_collection_by_type(db, image_type.value)

    total = collection.count_documents({})
    return total


@app.get("/image-plant/{image_type}/{image_id}")
def get_image_by_id(
    image_type: ImageType,
    image_id: int,
):
    collection = get_collection_by_type(db, image_type.value)

    doc = collection.find_one({"id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Image not found")

    doc.pop("_id", None)
    return doc
