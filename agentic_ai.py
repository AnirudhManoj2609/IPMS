from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import uuid
import json
import logging
import asyncio
import requests # Necessary for external API calls (Gemini)

# --- CONFIGURATION AND SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE: Simulated MongoDB Collections using in-memory dictionaries.
# In a production environment, replace these dictionaries with an async 
# connection using 'motor' (PyMongo async driver).
db: Dict[str, List[Dict[str, Any]]] = {
    "UserProfiles": [],      # User roles and preferences
    "Schedules": [],         # Core scheduling data (events, meetings, shoots)
    "Tasks": [],             # To-do items linked to schedules
    "Notifications": [],     # AI-generated alerts and reminders
}

# AI Configuration
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
API_URL_BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
API_KEY = "" # The runtime environment provides the key

# --- UTILITY AND MONGODB SIMULATION FUNCTIONS ---

def get_db_collection(collection_name: str) -> List[Dict[str, Any]]:
    """Retrieves the simulated collection."""
    if collection_name not in db:
        db[collection_name] = []
    return db[collection_name]

def db_find(collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Simulates db.collection.find(query). Simple key-value matching."""
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

# --- AGENTIC AI CORE LOGIC (Structured LLM Interaction) ---

async def call_gemini_api_structured(payload: Dict[str, Any], schema: Dict[str, Any], system_prompt: str, max_retries: int = 3) -> Optional[Any]:
    """Handles structured JSON API requests with exponential backoff."""
    full_payload = {
        **payload,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        },
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }
    
    for attempt in range(max_retries):
        try:
            # Using asyncio.to_thread for synchronous requests library in an async FastAPI context
            response = await asyncio.to_thread(
                lambda: requests.post(API_URL_BASE, headers={'Content-Type': 'application/json'}, json=full_payload, params={'key': API_KEY})
            )
            response.raise_for_status()
            
            result = response.json()
            json_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if json_text:
                return json.loads(json_text)
            return None
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Gemini API failed (Attempt {attempt+1}/{max_retries}). Retrying in {wait_time}s.")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Gemini API failed after {max_retries} attempts: {e}")
                return None
        except Exception as e:
            logger.error(f"Error processing Gemini structured response: {e}")
            # If JSON parsing fails, return the raw text for debugging
            logger.error(f"Raw response text: {json_text}")
            return None
    return None

async def run_agentic_audit(project_id: str) -> List[Dict[str, Any]]:
    """
    SIMULATED PROACTIVE AGENT MONITORING LOGIC
    
    In a real system, this function would:
    1. Query MongoDB for all pending schedules/tasks within the next 48 hours.
    2. Identify conflicting times or roles using efficient DB lookups (Step 1.2 in design).
    3. Construct a detailed data summary for the LLM.
    4. Call the LLM to generate actionable, prioritized notifications.
    """
    
    # 1. Simulate finding a critical anomaly (e.g., two mandatory events overlap)
    schedules = get_db_collection("Schedules")
    critical_data_for_llm = []
    
    # Simple simulation: Check if two events in the DB are marked as "conflict_pending"
    conflicts = db_find("Schedules", {"status": "conflict_pending"})
    
    if conflicts:
        critical_data_for_llm = [
            {"id": c['_id'], "event": c['event_type'], "user": c['user_id'], "start": c['start_time']}
            for c in conflicts[:2]
        ]
        
    if not critical_data_for_llm:
        # If no conflicts, the agent reports everything is fine
        return []

    # 2. Define the LLM's role and task
    system_prompt = (
        "You are the Master Production Scheduler AI. Analyze the critical scheduling data "
        "and generate a single, highly prioritized task list to resolve the conflict. "
        "Your task is to propose concrete, actionable solutions."
    )
    
    user_query = f"""
    The following CRITICAL scheduling conflicts were detected: 
    {json.dumps(critical_data_for_llm, indent=2)}.
    
    Generate a maximum of two CRITICAL tasks to resolve these conflicts.
    """
    
    # 3. Define the structured output schema for the LLM
    task_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "priority": {"type": "STRING", "enum": ["CRITICAL", "HIGH", "MEDIUM"]},
                "area": {"type": "STRING", "description": "Area affected (e.g., Scheduling, Personnel, Logistics)."},
                "action_required": {"type": "STRING", "description": "Specific action to take (e.g., 'Reschedule Director's meeting')."},
                "justification": {"type": "STRING", "description": "Data-driven reason."}
            },
            "required": ["priority", "area", "action_required", "justification"]
        }
    }
    
    # 4. Execute the structured API call
    tasks = await call_gemini_api_structured(
        payload={"contents": [{"parts": [{"text": user_query}]}]},
        schema=task_schema,
        system_prompt=system_prompt
    )
    
    if isinstance(tasks, list):
        # Insert generated notifications into the DB (Step 3.4 in design)
        for task in tasks:
            db_insert_one("Notifications", {
                "user_id": "production_manager", # Assume a single manager receives high-priority tasks
                "alert_type": task['priority'],
                "message": f"ACTION: {task['action_required']} | REASON: {task['justification']}",
                "is_delivered": False,
            })
        return tasks
    
    return []

# --- FASTAPI APPLICATION ---
app = FastAPI(title="Agentic AI Scheduling Server")

# --- CORE CRUD ENDPOINTS (Reactive Component) ---

@app.post("/user/profile")
async def create_user_profile(user_id: str = Form(...), role: str = Form(...), preferences: str = Form("{}")):
    """Add a new user profile with role and preferences."""
    profile = {
        "user_id": user_id,
        "role": role,
        "preferences": json.loads(preferences)
    }
    doc = db_insert_one("UserProfiles", profile)
    return {"message": "User profile created", "id": doc['_id']}

@app.post("/schedules/new")
async def create_schedule(
    user_id: str = Form(...),
    event_type: str = Form(...),
    start_time: str = Form(...), # ISO 8601 string
    end_time: str = Form(...),   # ISO 8601 string
    recurrence_rule: Optional[str] = Form(None)
):
    """
    Reactive endpoint for creating a new schedule item. 
    A real implementation would check for conflicts here.
    """
    try:
        datetime.fromisoformat(start_time)
        datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="start_time and end_time must be valid ISO 8601 strings.")

    schedule = {
        "user_id": user_id,
        "event_type": event_type,
        "start_time": start_time,
        "end_time": end_time,
        "recurrence_rule": recurrence_rule,
        "status": "Confirmed"
    }
    doc = db_insert_one("Schedules", schedule)
    return {"message": f"Schedule created for {user_id}", "schedule_id": doc['_id']}

# --- REACTIVE AI ENDPOINT (Natural Language to Structured Data) ---

@app.post("/ai/schedule_natural")
async def schedule_from_natural_language(prompt: str = Form(...), user_id: str = Form(...)):
    """
    Uses the AI to parse a natural language command into a structured schedule entry.
    """
    system_prompt = (
        "You are an AI Scheduling Parser. Convert the user's request into a single, clean JSON object "
        "following the provided schema. Infer the current date/time if relative terms are used (e.g., 'tomorrow')."
    )
    
    schedule_schema = {
        "type": "OBJECT",
        "properties": {
            "event_type": {"type": "STRING", "description": "Concise name of the event."},
            "start_time": {"type": "STRING", "description": "ISO 8601 datetime string for start time."},
            "end_time": {"type": "STRING", "description": "ISO 8601 datetime string for end time."},
            "duration_minutes": {"type": "INTEGER", "description": "Inferred duration in minutes (if not explicit)."}
        },
        "required": ["event_type", "start_time", "end_time"]
    }
    
    # Add context about the current date for relative scheduling
    context = f"Current Date: {datetime.utcnow().isoformat()}. User ID: {user_id}. Request: {prompt}"
    
    parsed_schedule = await call_gemini_api_structured(
        payload={"contents": [{"parts": [{"text": context}]}]},
        schema=schedule_schema,
        system_prompt=system_prompt
    )

    if not parsed_schedule:
        raise HTTPException(status_code=500, detail="AI failed to parse the natural language request.")

    # Convert the parsed JSON back into a DB entry structure
    schedule_entry = {
        "user_id": user_id,
        "event_type": parsed_schedule.get("event_type", "Untitled Event"),
        "start_time": parsed_schedule["start_time"],
        "end_time": parsed_schedule["end_time"],
        "status": "AI Draft"
    }
    
    doc = db_insert_one("Schedules", schedule_entry)
    
    return {
        "message": "Natural language request parsed and scheduled.",
        "schedule_id": doc['_id'],
        "parsed_data": parsed_schedule
    }

# --- PROACTIVE AGENT ENDPOINT (The Monitoring Brain) ---

@app.get("/agent/audit")
async def agentic_audit_status():
    """
    Triggers the Agentic AI's proactive audit and monitoring logic.
    Returns a list of actionable tasks generated by the LLM based on system analysis.
    """
    
    # In a real system, we'd iterate through project_ids. For this foundation, we use a single ID.
    project_id = "PROD-ALPHA-001" 
    
    tasks = await run_agentic_audit(project_id)
    
    if not tasks:
        return {
            "status": "GREEN",
            "message": "Agent completed audit. No critical scheduling conflicts found."
        }
    
    return {
        "status": "RED - ACTION REQUIRED",
        "message": "Critical conflicts detected. See tasks below.",
        "task_count": len(tasks),
        "tasks": tasks
    }

# --- HEALTH CHECK AND UTILITIES ---

@app.get("/status")
def get_db_status():
    """Returns the current state of the simulated database."""
    status = {
        "UserProfiles_Count": len(db["UserProfiles"]),
        "Schedules_Count": len(db["Schedules"]),
        "Tasks_Count": len(db["Tasks"]),
        "Notifications_Count": len(db["Notifications"]),
        "AI_Server": "Active",
        "DB_Simulation": "Running"
    }
    return status
