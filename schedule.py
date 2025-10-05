from fastapi import FastAPI, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import asyncio
import json
import logging
import motor
import requests
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware

# --- CONFIGURATION & SETUP ---
app = FastAPI(title="AI Production Scheduling Server")

# Load environment variables
load_dotenv()
MONGO_URL = os.getenv("MONGO") # Ensure this is correct and not falling back to localhost
DB_NAME = "production_scheduler"
API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
API_URL_BASE = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
if MONGO_URL:
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
else:
    # Use a print statement for debugging if connection is None
    print("MONGO_URL not found. Client may default to localhost:27017.")
    client = motor.motor_asyncio.AsyncIOMotorClient()
    db = client[DB_NAME]

# CORS setup for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas for Data Validation ---

class TeamInput(BaseModel):
    project_id: str = Field(..., example="PROD-EPIC-2025")
    team_name: str = Field(..., example="VFX Team")
    department: str = Field(..., example="Post-Production")
    lead_name: str = Field(..., example="Sarah Connor")
    
class ScheduleRequest(BaseModel):
    project_id: str = Field(..., example="PROD-EPIC-2025")
    day_number: int = Field(..., example=5)
    
class ScriptInput(BaseModel):
    project_id: str = Field(..., example="PROD-EPIC-2025")
    script_text: str = Field(..., example="SCENE 5 INT. HOSPITAL - NIGHT...")
    initial_planned_schedule: Dict[str, Any] = Field(..., example={"day_5": "Shoot Hospital Scenes"})

# --- DATABASE UTILITY FUNCTIONS ---

async def db_insert_one(collection_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
    collection = db[collection_name]
    result = await collection.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return document

async def db_find_one(collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    collection = db[collection_name]
    document = await collection.find_one(query)
    if document:
        document["_id"] = str(document["_id"])
    return document

async def db_find(collection_name: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
    collection = db[collection_name]
    results = []
    async for doc in collection.find(query):
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

# --- AI CALL FUNCTION ---

async def call_gemini_api(payload: Dict[str, Any]) -> Optional[str]:
    """Calls the Gemini API with retries and a focus on JSON output."""
    try:
        response = await asyncio.to_thread(
            lambda: requests.post(
                API_URL_BASE,
                headers={'Content-Type': 'application/json'},
                json=payload,
                params={'key': API_KEY}
            )
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract content, preferring parts that look like text
        candidate = result.get('candidates', [{}])[0]
        text = candidate.get('content', {}).get('parts', [{}])[0].get('text')
        
        return text
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API network error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing Gemini response: {e}")
        return None

# --- CORE AI SCHEDULING LOGIC ---

async def generate_daily_schedules(
    project_id: str, 
    day_number: int, 
    script_text: str, 
    teams: List[Dict[str, Any]], 
    delay_hours: int,
    initial_plan: Dict[str, Any]
) -> Dict[str, Any]:
    
    # 1. Format Team Data
    team_list_str = "\n".join([
        f"- {t['team_name']} ({t['department']}), Lead: {t['lead_name']}"
        for t in teams
    ])

    # 2. Determine Script Focus
    # For simplicity, we assume the AI can parse the script and focus on the day's scenes.
    day_key = f"day_{day_number}"
    planned_focus = initial_plan.get(day_key, "No specific plan found in initial schedule.")
    
    # 3. Construct System Prompt (Crucial for structured output)
    system_prompt = f"""
    You are an AI Assistant Director and Production Manager. Your task is to generate a comprehensive, actionable, time-blocked schedule for **EACH** team for **Shooting Day {day_number}** of the project "{project_id}".

    The goal is to provide specific tasks, times, and goals for each team based on the script, the planned schedule, and the current delay.

    --- CONSTRAINTS ---
    1. **Timeframe:** The shoot day is 12 hours (e.g., 8:00 AM to 8:00 PM), with 1 hour for lunch (1:00 PM to 2:00 PM).
    2. **Delay Adjustment:** The production is currently **{delay_hours} hours behind schedule**. Integrate tasks like "catch-up" or "prep for next day" to mitigate this delay.
    3. **Output Format:** You MUST return a single JSON object. The keys of this object MUST be the exact team names. The value for each team MUST be a list of tasks with 'time' and 'task' fields.
    
    --- EXAMPLE JSON OUTPUT ---
    {{
        "Production Team": [
            {{"time": "8:00 AM", "task": "Call Time & Safety Briefing"}},
            // ... more tasks
        ]
    }}
    """
    
    # 4. Construct User Query
    user_query = f"""
    Please generate the schedule for day {day_number}.

    **1. TEAMS INVOLVED:**
    {team_list_str}

    **2. SCRIPT CONTEXT (Day Focus):**
    Planned Focus for the Day: {planned_focus}

    [Script Snippet Relevant to Day {day_number}]
    {script_text[:1000]}... (Full script is available, focus on scenes relevant to the current plan)

    **3. PRODUCTION STATUS:**
    Cumulative Delay: {delay_hours} hours.

    Generate the JSON schedule now. Ensure the output is *only* the parsable JSON object.
    """
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    ai_response_text = await call_gemini_api(payload)
    
    if not ai_response_text:
        raise ValueError("AI failed to generate a schedule or API key is missing.")

    try:
        # Attempt to parse the AI's response as JSON
        # Gemini often wraps JSON in markdown, so we try to clean it
        cleaned_response = ai_response_text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse AI JSON response: {ai_response_text}")
        raise ValueError("AI returned an unparsable schedule format.")

# --- ENDPOINTS ---

@app.post("/teams/add/", summary="1. Add Production Team")
async def add_team(team_input: TeamInput):
    """Adds a new production team (e.g., VFX Team, Director Team, Art Department) to the project."""
    
    team_data = team_input.model_dump()
    
    # Check for duplicates before insertion
    existing = await db_find_one("teams", {"project_id": team_data["project_id"], "team_name": team_data["team_name"]})
    if existing:
        raise HTTPException(status_code=400, detail=f"Team '{team_data['team_name']}' already exists for this project.")

    doc = await db_insert_one("teams", team_data)
    return {"message": f"Team added: {doc['team_name']} ({doc['department']})", "team_id": doc['_id']}

@app.post("/script/upload/", summary="2. Upload Script and Initial Schedule")
async def upload_script(script_input: ScriptInput):
    """Uploads the full script and the initial planned schedule for comparison."""
    
    # Check if a script already exists for this project (we only expect one per project)
    existing = await db_find_one("scripts", {"project_id": script_input.project_id})
    if existing:
        raise HTTPException(status_code=400, detail="Script already exists. Use PUT or DELETE to modify/replace.")

    doc = await db_insert_one("scripts", script_input.model_dump())
    return {"message": f"Script and initial schedule uploaded for {script_input.project_id}", "script_id": doc['_id']}

@app.post("/schedule/generate/", summary="3. Generate Daily Team Schedules")
async def generate_schedule(schedule_request: ScheduleRequest):
    """Generates the AI-driven daily schedule for all teams based on current status and script."""
    
    project_id = schedule_request.project_id
    day_number = schedule_request.day_number

    # 1. Fetch Teams
    teams = await db_find("teams", {"project_id": project_id})
    if not teams:
        raise HTTPException(status_code=404, detail="No teams found for this project. Please add teams first.")

    # 2. Fetch Script and Initial Plan
    script_doc = await db_find_one("scripts", {"project_id": project_id})
    if not script_doc:
        raise HTTPException(status_code=404, detail="Script and initial schedule not found. Please upload them first.")
    
    # 3. Fetch Current Status/Delay
    # The 'production_status' collection would be updated by the logging server to track actual progress.
    # We assume a single document with the delay value.
    status_doc = await db_find_one("production_status", {"project_id": project_id})
    delay_hours = status_doc.get("cumulative_delay_hours", 0) if status_doc else 0

    try:
        # Call the core AI scheduling function
        team_schedules = await generate_daily_schedules(
            project_id=project_id,
            day_number=day_number,
            script_text=script_doc["script_text"],
            teams=teams,
            delay_hours=delay_hours,
            initial_plan=script_doc.get("initial_planned_schedule", {})
        )
        
        # 4. Save the generated schedule (for historical tracking and frontend comparison)
        schedule_log = {
            "project_id": project_id,
            "day_number": day_number,
            "delay_hours": delay_hours,
            "generated_schedules": team_schedules,
            "timestamp": str(db.client.admin.server_info()['localTime']),
        }
        await db_insert_one("daily_schedules", schedule_log)

        return {"day_number": day_number, "delay_hours": delay_hours, "schedules": team_schedules}

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schedule/history/{project_id}/{day_number}", summary="4. Retrieve Historical Schedule")
async def get_schedule_history(project_id: str, day_number: int):
    """Retrieves the last generated schedule for a specific day number."""
    
    schedule_doc = await db_find_one(
        "daily_schedules", 
        {"project_id": project_id, "day_number": day_number}
    )

    if not schedule_doc:
        raise HTTPException(status_code=404, detail=f"No generated schedule found for Day {day_number}.")

    # Fetch initial plan for frontend comparison
    script_doc = await db_find_one("scripts", {"project_id": project_id})
    initial_plan = script_doc.get("initial_planned_schedule", {}).get(f"day_{day_number}", "Plan not detailed.")

    return {
        "day_number": day_number,
        "delay_hours": schedule_doc["delay_hours"],
        "initial_planned_focus": initial_plan,
        "schedules": schedule_doc["generated_schedules"]
    }

# --- EXAMPLE ENDPOINT for Simulating Status Update ---
@app.post("/status/update/", summary="FOR TESTING: Update Current Delay")
async def update_delay(project_id: str = Form(...), cumulative_delay_hours: int = Form(...)):
    """Allows simulating the cumulative delay status, which the scheduler uses to adjust."""
    
    # This simulates a progress tracking system updating the delay
    result = await db["production_status"].update_one(
        {"project_id": project_id},
        {"$set": {"cumulative_delay_hours": cumulative_delay_hours}},
        upsert=True
    )
    return {"message": f"Delay status updated for {project_id}. Current delay: {cumulative_delay_hours} hours."}