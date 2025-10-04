from fastapi import FastAPI, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import asyncio
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# --- MONGODB SETUP ---
MONGO_URL = os.getenv("MONGO")
DB_NAME = "budget_tracker"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# --- AI CONFIGURATION ---
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
API_URL_BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
API_KEY = os.getenv("GEMINI_API_KEY")

# --- FASTAPI APP ---
app = FastAPI(title="AI Movie Production Tracker (MongoDB Extended)")

# --- CORS CONFIGURATION ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE HELPERS ---
async def db_insert_one(collection_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
    collection = db[collection_name]
    result = await collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return document

async def db_find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    collection = db[collection_name]
    doc = await collection.find_one(query)
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc

async def db_find(collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    collection = db[collection_name]
    results = []
    async for d in collection.find(query):
        d["_id"] = str(d["_id"])
        results.append(d)
    return results

async def get_all_personnel(project_id: str):
    return await db_find("personnel", {"project_id": project_id})

# --- EXISTING ENDPOINTS KEPT UNTOUCHED ---
# (keep your previous endpoints here as they are)
# add_personnel, log_attendance, log_item_collection, log_resource_usage, etc.

# --- EXTENDED ENDPOINTS ---

@app.post("/personnel/add/extended/")
async def add_personnel_extended(data: Dict[str, Any] = Body(...)):
    """Add a new crew member (extended, JSON-based)."""
    project_id = data.get("project_id")
    name = data.get("name")
    role = data.get("role")
    is_role_lead = data.get("is_role_lead", False)
    leader_name = data.get("leader_name")

    leader_id = None
    if leader_name:
        leader_doc = await db_find_one("personnel", {"project_id": project_id, "name": leader_name})
        if not leader_doc:
            raise HTTPException(status_code=404, detail=f"Leader '{leader_name}' not found.")
        leader_id = leader_doc["_id"]

    person = {
        "project_id": project_id,
        "name": name,
        "role": role,
        "is_role_lead": is_role_lead,
        "leader_id": leader_id,
        "created_at": datetime.utcnow().isoformat()
    }

    doc = await db_insert_one("personnel", person)
    return {"message": f"Extended personnel added: {name} ({role})", "person_id": doc["_id"]}

# --- EXTENDED ATTENDANCE ---
@app.post("/attendance/log/extended/")
async def log_attendance_extended(data: Dict[str, Any] = Body(...)):
    """Log extended attendance with wages and food."""
    project_id = data.get("project_id")
    report_date = data.get("date")
    reporter_name = data.get("reporter_name")
    attendance = data.get("attendance", [])  # list of {name, present, wage, food_cost}

    reporter_doc = await db_find_one("personnel", {"project_id": project_id, "name": reporter_name})
    if not reporter_doc:
        raise HTTPException(status_code=403, detail="Reporter not recognized.")

    existing_log = await db_find_one("attendance_extended", {"project_id": project_id, "date": report_date})
    if existing_log:
        raise HTTPException(status_code=400, detail=f"Attendance log already exists for {report_date}.")

    total_present = sum(1 for a in attendance if a.get("present"))
    total_absent = sum(1 for a in attendance if not a.get("present"))
    total_wage = sum(float(a.get("wage", 0)) for a in attendance)
    total_food = sum(float(a.get("food_cost", 0)) for a in attendance)

    log = {
        "project_id": project_id,
        "date": report_date,
        "reporter_name": reporter_name,
        "attendance": attendance,
        "summary": {
            "present_count": total_present,
            "absent_count": total_absent,
            "total_wage": total_wage,
            "total_food": total_food
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    doc = await db_insert_one("attendance_extended", log)
    return {"message": "Extended attendance logged successfully", "log_id": doc["_id"]}

# --- EXTENDED ITEM COLLECTION ---
@app.post("/items/log/extended/")
async def log_items_extended(data: Dict[str, Any] = Body(...)):
    """Log extended item collection list."""
    project_id = data.get("project_id")
    report_date = data.get("date")
    reporter_name = data.get("reporter_name")
    items = data.get("items", [])  # list of {name, quantity, unit_cost, hour, action, lead}

    reporter_doc = await db_find_one("personnel", {"project_id": project_id, "name": reporter_name})
    if not reporter_doc:
        raise HTTPException(status_code=403, detail="Reporter not recognized.")

    total_cost = sum(float(i.get("unit_cost", 0)) * float(i.get("quantity", 1)) for i in items)
    log = {
        "project_id": project_id,
        "date": report_date,
        "reporter_name": reporter_name,
        "items": items,
        "total_cost": total_cost,
        "timestamp": datetime.utcnow().isoformat()
    }

    doc = await db_insert_one("item_collection_extended", log)
    return {"message": "Extended item collection logged", "log_id": doc["_id"]}

# --- EXTENDED RESOURCE USAGE ---
@app.post("/resources/log/extended/")
async def log_resources_extended(data: Dict[str, Any] = Body(...)):
    """Log extended resource usage list."""
    project_id = data.get("project_id")
    report_date = data.get("date")
    reporter_name = data.get("reporter_name")
    resources = data.get("resources", [])  # list of {resource_type, item_name, quantity, cost, lead, notes}

    reporter_doc = await db_find_one("personnel", {"project_id": project_id, "name": reporter_name})
    if not reporter_doc:
        raise HTTPException(status_code=403, detail="Reporter not recognized.")

    total_cost = sum(float(r.get("cost", 0)) * float(r.get("quantity", 1)) for r in resources)
    log = {
        "project_id": project_id,
        "date": report_date,
        "reporter_name": reporter_name,
        "resources": resources,
        "total_cost": total_cost,
        "timestamp": datetime.utcnow().isoformat()
    }

    doc = await db_insert_one("resource_usage_extended", log)
    return {"message": "Extended resource usage logged", "log_id": doc["_id"]}

@app.get("/")
async def root():
    return {"message": "AI Movie Production Tracker API (Extended)", "status": "operational"}

@app.on_event("startup")
async def startup_event():
    logger.info("Server started with extended endpoints.")
    logger.info(f"Connected to MongoDB: {DB_NAME}")

@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    logger.info("MongoDB connection closed.")
