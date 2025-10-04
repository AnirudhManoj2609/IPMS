from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import uuid
import json
import logging
import asyncio
import random
import numpy as np

# --- CONFIGURATION AND SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE: Since this is a single, self-contained file execution environment, 
# we are simulating MongoDB collections using in-memory dictionaries. 
# In a real app, you would use 'motor' (async PyMongo driver) here.

# Simulated MongoDB Collections
db: Dict[str, List[Dict[str, Any]]] = {
    "personnel": [],      # Crew members and their roles/leaders
    "attendance": [],     # Daily check-in/absence records
    "resource_usage": [], # Daily tracking of props, equipment, etc.
    "daily_logs": []      # AI-generated daily summaries
}

# AI Configuration (Placeholders for Gemini API)
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
API_URL_BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
API_KEY = "" # The runtime environment provides the key

# --- UTILITY AND MONGODB SIMULATION FUNCTIONS ---

def get_db_collection(collection_name: str) -> List[Dict[str, Any]]:
    """Retrieves the simulated collection."""
    return db[collection_name]

def db_find(collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Simulates db.collection.find(query)."""
    collection = get_db_collection(collection_name)
    results = []
    for doc in collection:
        match = True
        for key, value in query.items():
            if doc.get(key) != value:
                match = False
                break
        if match:
            results.append(doc)
    return results

def db_find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Simulates db.collection.find_one(query)."""
    results = db_find(collection_name, query)
    return results[0] if results else None

def db_insert_one(collection_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates db.collection.insert_one(document)."""
    document["_id"] = str(uuid.uuid4())
    document["created_at"] = datetime.utcnow().isoformat()
    get_db_collection(collection_name).append(document)
    return document

# --- AI CORE LOGIC (Using Simulated LLM Calls) ---

async def call_gemini_api(payload: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
    """Handles the network request to the Gemini API with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                lambda: requests.post(API_URL_BASE, headers={'Content-Type': 'application/json'}, json=payload, params={'key': API_KEY})
            )
            response.raise_for_status()
            
            result = response.json()
            candidate = result.get('candidates', [{}])[0]
            text = candidate.get('content', {}).get('parts', [{}])[0].get('text')
            return text
        
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Gemini API failed after {max_retries} attempts: {e}")
                return None
        except Exception as e:
            logger.error(f"Error processing Gemini response: {e}")
            return None
    return None

def analyze_historical_data(collection_name: str, project_id: str, key: str) -> Dict[str, Any]:
    """
    Simulates historical analysis for anomaly detection.
    In a real MongoDB setup, this would be an aggregate query.
    """
    
    # 1. Calculate past 7 days average usage
    seven_days_ago = (datetime.utcnow().date() - timedelta(days=7)).isoformat()
    
    recent_docs = [
        doc for doc in db_find(collection_name, {"project_id": project_id})
        if doc.get("date", "1970-01-01") >= seven_days_ago
    ]
    
    if not recent_docs:
        return {"average": 0, "std_dev": 0, "trend": "new_data"}
    
    # Simple average for demonstration (e.g., average count of resources/attendance)
    if collection_name == "attendance":
        present_counts = [len([p for p in doc.get("present_ids", [])]) for doc in recent_docs]
        absent_counts = [len([a for a in doc.get("absent_ids", [])]) for doc in recent_docs]
        
        avg_present = np.mean(present_counts) if present_counts else 0
        avg_absent = np.mean(absent_counts) if absent_counts else 0
        
        return {
            "avg_present": round(avg_present), 
            "avg_absent": round(avg_absent), 
            "present_std": np.std(present_counts) if present_counts else 0
        }
    
    return {"average": 0, "std_dev": 0, "trend": "stable"}


async def generate_ai_report(project_id: str, report_date: str) -> str:
    """
    Uses the Gemini API to synthesize raw data into a narrative daily production report.
    This is the core 'AI' dynamic reporting feature.
    """
    
    # --- 1. Fetch Raw Data for the Day ---
    attendance_data = db_find_one("attendance", {"project_id": project_id, "date": report_date})
    resource_data = db_find("resource_usage", {"project_id": project_id, "date": report_date})
    all_personnel = get_db_collection("personnel")
    
    if not attendance_data and not resource_data:
        return "No data logged for this date. Cannot generate AI report."

    # --- 2. Perform Anomaly Detection and Contextualization ---
    
    # Attendance Analysis
    attendance_summary = ""
    if attendance_data:
        present_count = len(attendance_data.get("present_ids", []))
        absent_count = len(attendance_data.get("absent_ids", []))
        
        hist_attendance = analyze_historical_data("attendance", project_id, "present_ids")
        
        anomaly_status = ""
        if present_count < hist_attendance.get("avg_present", 0) - hist_attendance.get("present_std", 0) * 1.5:
            anomaly_status = f"CRITICAL ANOMALY: Crew present ({present_count}) is significantly lower than average ({hist_attendance['avg_present']}). Production likely impacted."
        elif absent_count > hist_attendance.get("avg_absent", 0) + hist_attendance.get("present_std", 0):
            anomaly_status = f"WARNING: Absent count ({absent_count}) is slightly higher than usual."
        else:
            anomaly_status = "Attendance is stable and on track with historical averages."
            
        absent_names = [p['name'] for p in all_personnel if p['_id'] in attendance_data.get("absent_ids", [])]
        
        attendance_summary = f"""
        - Total Crew Present: {present_count}
        - Total Crew Absent: {absent_count}
        - Absent List: {', '.join(absent_names) if absent_names else 'None'}
        - Historical Alert: {anomaly_status}
        """

    # Resource Analysis
    resource_summary = ""
    if resource_data:
        resource_items = [f"{r['resource_type']}: {r['item_name']} (Qty: {r['quantity']})" for r in resource_data]
        resource_summary = "\n- ".join(["Resources Logged:"] + resource_items)

    # --- 3. Construct LLM Prompt ---
    
    system_prompt = (
        "You are an AI Production Coordinator. Your task is to analyze the raw daily logs "
        "and generate a single, highly concise, narrative summary report for the film's "
        "Executive Producer. Focus on deviations, critical attendance issues, and resource use."
        "The report should be professional and actionable, with a title and three paragraphs."
    )
    
    user_query = f"""
    Generate a Daily Production Status Report for {report_date} based on the following raw data.
    
    --- Attendance Data ---
    {attendance_summary}
    
    --- Resource Usage ---
    {resource_summary}
    """
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    # --- 4. Call Gemini API ---
    ai_report_text = await call_gemini_api(payload)
    
    if not ai_report_text:
        return "Failed to generate AI report due to API error."
        
    # --- 5. Save Report to DB ---
    db_insert_one("daily_logs", {
        "project_id": project_id,
        "date": report_date,
        "report_text": ai_report_text,
    })
    
    return ai_report_text

# --- FASTAPI APPLICATION ---
app = FastAPI(title="AI Movie Production Tracker (MongoDB Simulation)")

@app.post("/personnel/add/")
async def add_personnel(
    project_id: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    leader_name: Optional[str] = Form(None)
):
    """
    Adds a crew member with their role and reporting leader.
    """
    leader_id = None
    if leader_name:
        leader_doc = db_find_one("personnel", {"project_id": project_id, "name": leader_name})
        if not leader_doc:
            raise HTTPException(status_code=404, detail=f"Leader '{leader_name}' not found. Add the leader first.")
        leader_id = leader_doc['_id']
        
    person = {
        "project_id": project_id,
        "name": name,
        "role": role,
        "leader_id": leader_id
    }
    
    doc = db_insert_one("personnel", person)
    return {"message": f"Personnel added: {name} ({role})", "person_id": doc['_id']}

@app.post("/attendance/log/")
async def log_attendance(
    project_id: str = Form(...),
    report_date: str = Form(...),
    present_names: List[str] = Form([]),
    absent_names: List[str] = Form([]),
    reporter_name: str = Form(...) # The leader reporting the status
):
    """
    Logs attendance for a specific day. Requires names of present and absent crew.
    Only allows one attendance log per day per project.
    """
    
    # 1. Check if the reporter is a registered crew member
    reporter_doc = db_find_one("personnel", {"project_id": project_id, "name": reporter_name})
    if not reporter_doc:
        raise HTTPException(status_code=403, detail="Reporter not recognized in personnel list.")

    # 2. Check for existing log
    if db_find_one("attendance", {"project_id": project_id, "date": report_date}):
        raise HTTPException(status_code=400, detail=f"Attendance log already exists for {report_date}. Use a PUT/UPDATE method to modify.")
        
    all_personnel_docs = db_find("personnel", {"project_id": project_id})
    name_to_id = {p['name']: p['_id'] for p in all_personnel_docs}

    present_ids = [name_to_id.get(name) for name in present_names if name in name_to_id]
    absent_ids = [name_to_id.get(name) for name in absent_names if name in name_to_id]
    
    if len(present_ids) + len(absent_ids) != len(all_personnel_docs):
        logger.warning("Mismatched attendance: not all crew accounted for.")

    attendance_log = {
        "project_id": project_id,
        "date": report_date,
        "reported_by_id": reporter_doc['_id'],
        "present_ids": present_ids,
        "absent_ids": absent_ids
    }
    
    doc = db_insert_one("attendance", attendance_log)
    return {"message": f"Attendance logged for {report_date}", "attendance_id": doc['_id']}

@app.post("/resources/log/")
async def log_resource_usage(
    project_id: str = Form(...),
    report_date: str = Form(...),
    resource_type: str = Form(...),
    item_name: str = Form(...),
    quantity: int = Form(1),
    notes: Optional[str] = Form(None)
):
    """
    Tracks resource or equipment usage for the day.
    """
    resource_log = {
        "project_id": project_id,
        "date": report_date,
        "resource_type": resource_type, # e.g., Camera, Prop, Location Area
        "item_name": item_name,
        "quantity": quantity,
        "notes": notes
    }
    
    doc = db_insert_one("resource_usage", resource_log)
    return {"message": f"Resource usage logged for {item_name}", "log_id": doc['_id']}

@app.get("/report/daily_summary/{project_id}/{report_date}")
async def get_daily_summary(project_id: str, report_date: str):
    """
    Generates the AI-enhanced daily summary report by synthesizing all logged data.
    This feature is dynamic and high-value.
    """
    
    # 1. Check if report already exists
    existing_report = db_find_one("daily_logs", {"project_id": project_id, "date": report_date})
    if existing_report:
        return {
            "status": "cached",
            "date": report_date,
            "report": existing_report["report_text"]
        }
        
    # 2. Generate and save new report
    report_text = await generate_ai_report(project_id, report_date)
    
    if "Failed to generate AI report" in report_text:
        raise HTTPException(status_code=500, detail=report_text)
        
    return {
        "status": "generated",
        "date": report_date,
        "report": report_text
    }

@app.get("/data/status/{project_id}")
async def get_project_status(project_id: str):
    """
    Provides a quick status overview of the project's data fidelity.
    """
    total_crew = len(db_find("personnel", {"project_id": project_id}))
    total_attendance_days = len(db_find("attendance", {"project_id": project_id}))
    total_resource_logs = len(db_find("resource_usage", {"project_id": project_id}))
    total_ai_reports = len(db_find("daily_logs", {"project_id": project_id}))
    
    return {
        "project_id": project_id,
        "data_integrity": {
            "total_crew_members": total_crew,
            "attendance_logs_count": total_attendance_days,
            "resource_logs_count": total_resource_logs,
            "ai_reports_generated": total_ai_reports
        },
        "message": "Data structures are ready for logging."
    }
