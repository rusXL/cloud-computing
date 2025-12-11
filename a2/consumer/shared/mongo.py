# Mongo helper
from pymongo.database import Database, Collection
from pymongo import MongoClient
from pymongo.database import Database
import os

# Config
MONGO = os.environ.get("MONGO", "mongodb://localhost:27018")
DB_NAME = "imagedbplantconsumer"


def get_collection_by_type(db: Database, plant_type: str) -> Collection:
    return db[f"imagecolplant{plant_type}"]


def get_client() -> MongoClient:
    client = MongoClient(MONGO)
    client.admin.command("ping")
    return client


def get_db(client: MongoClient = None) -> Database:
    if client is None:
        client = get_client()
    return client[DB_NAME]
