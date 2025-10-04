import os
import re
import json
from io import BytesIO
from typing import List, Union
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2
from groq import Groq

# --- Initialization ---
app = FastAPI(title="Unified Script Analyzer AI", version="1.0.0")
client = Groq(api_key="KEYY") # Replace KEYY with your actual Groq API key

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Shared Utilities ---

def extract_text_from_pdf(pdf_file: BytesIO) -> (str, int):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    full_text = ""
    page_count = 0
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n\n"
            page_count += 1
    return full_text, page_count

def call_groq(prompt: str, max_tokens: int, temperature: float = 0.3) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def extract_json_from_response(response_text: str) -> str:
    # Extracts JSON object from response, handling markdown fences (```json)
    json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return response_text

def split_script_into_chunks(script_text: str, chunk_size_pages=5):
    # Splits script text for models with token limits
    words = script_text.split()
    chunk_size_words = chunk_size_pages * 250
    chunks = [ " ".join(words[i:i+chunk_size_words]) for i in range(0, len(words), chunk_size_words)]
    return chunks

# --- 1. Director/Production Models ---

class DirectorCharacter(BaseModel):
    name: str
    role: str
    description: str
    first_appearance_scene: int
    total_scenes: int
    suggested_casting_notes: str

class DirectorLocation(BaseModel):
    name: str
    type: str
    scenes: List[int]
    total_scenes: int
    logistical_notes: str
    estimated_setup_complexity: str

class DirectorProp(BaseModel):
    name: str
    category: str
    scenes: List[int]
    importance: str
    description: str

class DirectorSpecialRequirement(BaseModel):
    type: str
    description: str
    scenes: List[int]
    complexity: str
    estimated_cost_impact: str

class DirectorScene(BaseModel):
    scene_number: int
    scene_heading: str
    int_ext: str
    location: str
    time_of_day: str
    page_count: float
    description: str
    characters: List[str]
    props: List[str]
    special_requirements: List[str]
    estimated_setup_time_minutes: int
    estimated_shoot_time_minutes: int
    complexity_score: int

class DirectorScriptAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    estimated_shoot_days: int
    estimated_budget_range: str
    scenes: List[DirectorScene]
    characters: List[DirectorCharacter]
    locations: List[DirectorLocation]
    props: List[DirectorProp]
    special_requirements: List[DirectorSpecialRequirement]
    genre: str
    tone: str
    shooting_complexity: str
    key_challenges: List[str]
    budget_considerations: List[str]
    scheduling_recommendations: List[str]

# --- 2. Cinematography Models ---

class CameraEquipment(BaseModel):
    camera_body: str
    lenses_required: List[str]
    stabilization: List[str]
    specialty_rigs: List[str]
    filters_needed: List[str]
    justification: str

class CameraLightingSetup(BaseModel):
    scene_number: int
    location: str
    time_of_day: str
    lighting_style: str
    key_lights: List[str]
    fill_lights: List[str]
    practical_lights: List[str]
    modifiers_needed: List[str]
    power_requirements: str
    setup_complexity: str
    estimated_setup_time_minutes: int

class CameraShot(BaseModel):
    shot_number: str
    scene_number: int
    shot_type: str
    shot_size: str
    camera_angle: str
    camera_movement: str
    lens_focal_length: str
    aperture_recommendation: str
    frame_rate: str
    stabilization_required: str
    special_equipment: List[str]
    lighting_notes: str
    composition_notes: str
    estimated_setup_time_minutes: int
    estimated_shoot_time_minutes: int
    technical_difficulty: str

class CameraScene(BaseModel):
    scene_number: int
    scene_heading: str
    int_ext: str
    location: str
    time_of_day: str
    page_count: float
    description: str
    total_shots_estimated: int
    primary_camera_positions: List[str]
    recommended_camera_package: str
    lighting_approach: str
    power_requirements: str
    crew_size_recommendation: int
    gimbal_required: bool
    crane_dolly_required: bool
    drone_required: bool
    underwater_required: bool
    special_fps_required: str
    color_temperature_notes: str
    estimated_setup_time_minutes: int
    estimated_shoot_time_minutes: int
    technical_complexity_score: int

class CameraMovement(BaseModel):
    movement_type: str
    scenes: List[int]
    total_occurrences: int
    equipment_needed: str
    crew_expertise_level: str
    notes: str

class CameraVisualEffect(BaseModel):
    effect_type: str
    description: str
    scenes: List[int]
    camera_requirements: str
    pre_production_notes: str
    on_set_requirements: str
    post_production_notes: str

class CameraScriptAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    estimated_shoot_days: int
    overall_visual_style: str
    cinematography_genre: str
    aspect_ratio_recommendation: str
    color_grading_approach: str
    reference_films: List[str]
    scenes: List[CameraScene]
    shots: List[CameraShot]
    lighting_setups: List[CameraLightingSetup]
    camera_equipment: CameraEquipment
    camera_movements: List[CameraMovement]
    visual_effects: List[CameraVisualEffect]
    overall_technical_complexity: str
    key_technical_challenges: List[str]
    pre_production_requirements: List[str]
    equipment_rental_budget_estimate: str
    crew_recommendations: dict
    location_scouting_priorities: List[str]

# --- New Unified Response Model ---
class AllAnalysesResult(BaseModel):
    script_title: str
    total_pages: int
    director_analysis: Union[DirectorScriptAnalysis, dict, None] = None
    cinematographer_analysis: Union[CameraScriptAnalysis, dict, None] = None


# --- 3. Role-Specific Analysis Functions (Full Prompts Inserted) ---

def analyze_for_director(script_text: str, page_count: int) -> dict:
    # Full prompt for the Director/Production role
    prompt = f"""
You are an expert film director and production manager. Analyze this script for character, location, logistics, casting, and overall production planning.
Your primary focus is on the human element, logistics, budget, and schedule.

Return ONLY a JSON matching this schema exactly. Do not wrap it in markdown code blocks:

{{
  "script_title": "string",
  "total_pages": {page_count},
  "total_scenes": 0,
  "estimated_shoot_days": 0,
  "estimated_budget_range": "string",
  "characters": [
    {{
      "name": "string",
      "role": "string",
      "description": "string",
      "first_appearance_scene": 0,
      "total_scenes": 0,
      "suggested_casting_notes": "string"
    }}
  ],
  "locations": [
    {{
      "name": "string",
      "type": "INT/EXT",
      "scenes": [0],
      "total_scenes": 0,
      "logistical_notes": "string",
      "estimated_setup_complexity": "Low/Medium/High"
    }}
  ],
  "props": [
    {{
      "name": "string",
      "category": "string",
      "scenes": [0],
      "importance": "Low/Medium/High",
      "description": "string"
    }}
  ],
  "special_requirements": [
    {{
      "type": "string",
      "description": "string",
      "scenes": [0],
      "complexity": "Low/Medium/High",
      "estimated_cost_impact": "Low/Medium/High"
    }}
  ],
  "scenes": [
    {{
      "scene_number": 0,
      "scene_heading": "string",
      "int_ext": "INT/EXT",
      "location": "string",
      "time_of_day": "string",
      "page_count": 0,
      "description": "string",
      "characters": ["string"],
      "props": ["string"],
      "special_requirements": ["string"],
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "complexity_score": 0
    }}
  ],
  "genre": "string",
  "tone": "string",
  "shooting_complexity": "Low/Medium/High",
  "key_challenges": ["string"],
  "budget_considerations": ["string"],
  "scheduling_recommendations": ["string"]
}}

Analyze this script and fill in all fields exactly as above. For the suggested_casting_notes field in each character, provide multiple suggestions (at least 2-3) of only **Malayalam and other Indian actors** who excel in similar roles. For characters under 18, suggest only actors who are close to the character’s age. Do not suggest adult actors. Include their age, experience, and IMDb ratings if possible based on their performances in recent movies (from the last 5-10 years), current trends, and stardom. Include references to their IMDb ratings for relevant films or overall, and explain why they fit the role. Format the notes as a bulleted list, e.g., '- Actor Name: Reason including recent movie examples and IMDb rating.'. Script:
{script_text}
"""
    response_text = call_groq(prompt, max_tokens=8000) # Director analysis can be large
    json_text = extract_json_from_response(response_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response as JSON for Director: {str(e)}")

def analyze_for_cinematographer(script_text: str, page_count: int) -> dict:
    # Full prompt for the Cinematographer role
    prompt = f"""
You are an expert cinematographer and camera department head. Analyze this script ONLY from the camera team's perspective.

Return ONLY a JSON matching this schema exactly. Do not wrap it in markdown code blocks:

{{
  "script_title": "string",
  "total_pages": {page_count},
  "total_scenes": 0,
  "estimated_shoot_days": 0,
  "overall_visual_style": "string (e.g., naturalistic, stylized, documentary, noir, etc.)",
  "cinematography_genre": "string",
  "aspect_ratio_recommendation": "string (e.g., 2.39:1, 1.85:1, 16:9)",
  "color_grading_approach": "string (e.g., warm/cool tones, high contrast, desaturated)",
  "reference_films": ["film names with similar visual style"],
  "scenes": [
    {{
      "scene_number": 0,
      "scene_heading": "string",
      "int_ext": "INT/EXT",
      "location": "string",
      "time_of_day": "string",
      "page_count": 0.0,
      "description": "string",
      "total_shots_estimated": 0,
      "primary_camera_positions": ["positions like wide master, close-ups, OTS, etc."],
      "recommended_camera_package": "string (e.g., Arri Alexa Mini, RED Komodo, etc.)",
      "lighting_approach": "string (e.g., natural light, three-point, motivated practicals)",
      "power_requirements": "string (e.g., 100A service, battery-powered, etc.)",
      "crew_size_recommendation": 0,
      "gimbal_required": false,
      "crane_dolly_required": false,
      "drone_required": false,
      "underwater_required": false,
      "special_fps_required": "string (24fps, 48fps, 120fps, etc.)",
      "color_temperature_notes": "string (e.g., 5600K daylight, 3200K tungsten mix)",
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "technical_complexity_score": 0
    }}
  ],
  "shots": [
    {{
      "shot_number": "string (e.g., 1A, 1B, 2A)",
      "scene_number": 0,
      "shot_type": "string (master, coverage, insert, etc.)",
      "shot_size": "string (ECU, CU, MCU, MS, MLS, LS, ELS, etc.)",
      "camera_angle": "string (eye-level, high, low, dutch, POV, etc.)",
      "camera_movement": "string (static, pan, tilt, dolly, tracking, handheld, etc.)",
      "lens_focal_length": "string (e.g., 24mm, 50mm, 85mm, 24-70mm zoom)",
      "aperture_recommendation": "string (e.g., f/2.8, f/5.6, f/8)",
      "frame_rate": "string (24fps, 48fps, 120fps, etc.)",
      "stabilization_required": "string (tripod, gimbal, steadicam, dolly, handheld, etc.)",
      "special_equipment": ["list of special gear needed"],
      "lighting_notes": "string (describe lighting setup for this shot)",
      "composition_notes": "string (rule of thirds, leading lines, symmetry, etc.)",
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "technical_difficulty": "Low/Medium/High"
    }}
  ],
  "lighting_setups": [
    {{
      "scene_number": 0,
      "location": "string",
      "time_of_day": "string",
      "lighting_style": "string (naturalistic, dramatic, high-key, low-key, etc.)",
      "key_lights": ["list of key lights needed, e.g., ARRI M18, Aputure 600D"],
      "fill_lights": ["list of fill lights"],
      "practical_lights": ["list of practical lights in scene"],
      "modifiers_needed": ["softboxes, diffusion, flags, scrims, etc."],
      "power_requirements": "string",
      "setup_complexity": "Low/Medium/High",
      "estimated_setup_time_minutes": 0
    }}
  ],
  "camera_equipment": {{
    "camera_body": "string (recommended primary camera)",
    "lenses_required": ["list of lenses needed for entire production"],
    "stabilization": ["tripods, gimbals, steadicam, etc."],
    "specialty_rigs": ["crane, dolly, drone, underwater housing, etc."],
    "filters_needed": ["ND filters, polarizers, mist filters, etc."],
    "justification": "string (explain why this package)"
  }},
  "camera_movements": [
    {{
      "movement_type": "string (dolly, crane, steadicam, handheld, etc.)",
      "scenes": [0],
      "total_occurrences": 0,
      "equipment_needed": "string",
      "crew_expertise_level": "string (basic, intermediate, expert)",
      "notes": "string"
    }}
  ],
  "visual_effects": [
    {{
      "effect_type": "string (green screen, wire removal, CGI, etc.)",
      "description": "string",
      "scenes": [0],
      "camera_requirements": "string (specific camera settings, markers, tracking points)",
      "pre_production_notes": "string",
      "on_set_requirements": "string (what camera team needs to capture)",
      "post_production_notes": "string"
    }}
  ],
  "overall_technical_complexity": "Low/Medium/High",
  "key_technical_challenges": ["list of main camera/lighting challenges"],
  "pre_production_requirements": ["tech scouts, camera tests, lighting tests, etc."],
  "equipment_rental_budget_estimate": "string (e.g., $15,000-$25,000 for 10 days)",
  "crew_recommendations": {{
    "director_of_photography": 1,
    "camera_operators": 0,
    "first_ac": 0,
    "second_ac": 0,
    "dit": 0,
    "gaffer": 1,
    "best_boy_electric": 0,
    "electricians": 0,
    "key_grip": 1,
    "best_boy_grip": 0,
    "grips": 0,
    "steadicam_operator": 0,
    "drone_operator": 0
  }},
  "location_scouting_priorities": ["list of what to look for during scouts from camera perspective"]
}}

Analyze this script comprehensively from the camera department's perspective. Break down each scene into estimated shots with specific technical details. Consider lighting, equipment, movements, and all technical requirements. Be detailed and specific.

Script:
{script_text}
"""
    response_text = call_groq(prompt, max_tokens=8000)
    json_text = extract_json_from_response(response_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response as JSON for Cinematographer: {str(e)}")


# --- 4. The Unified Endpoint (Looped Dispatcher) ---

@app.post("/analyze-script-pdf", response_model=AllAnalysesResult)
async def analyze_script_pdf(
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    pdf_bytes = await file.read()
    script_text, page_count = extract_text_from_pdf(BytesIO(pdf_bytes))
    if len(script_text) < 100:
        raise HTTPException(status_code=400, detail="PDF content too short")

    # Define all roles to run the analysis for
    ROLES_TO_ANALYZE = ["director", "cinematographer"]
    
    results = {
        "script_title": "Script Analysis In Progress", # Default title
        "total_pages": page_count,
    }

    # Loop through roles to get all required analyses
    for role in ROLES_TO_ANALYZE:
        print(f"Starting analysis for role: {role}")

        try:
            if role == "director":
                # Director analysis: single model call
                analysis = analyze_for_director(script_text, page_count)
                # Pydantic validation and assignment
                results["director_analysis"] = DirectorScriptAnalysis(**analysis) 
                # Update main title from the first successful analysis
                if "script_title" in analysis:
                    results["script_title"] = analysis["script_title"]
                
            elif role == "cinematographer":
                # Cinematographer analysis: requires chunking and merging
                chunks = split_script_into_chunks(script_text, chunk_size_pages=5)
                combined_scenes = []
                combined_shots = []
                last_chunk_analysis = {}

                for chunk in chunks:
                    chunk_analysis = analyze_for_cinematographer(chunk, page_count=round(len(chunk.split())/250))
                    # Merge lists from all chunks
                    combined_scenes.extend(chunk_analysis.get("scenes", []))
                    combined_shots.extend(chunk_analysis.get("shots", []))
                    last_chunk_analysis = chunk_analysis # Keep the latest one for top-level data

                analysis = {
                    **last_chunk_analysis,
                    "scenes": combined_scenes,
                    "shots": combined_shots,
                }
                # Pydantic validation and assignment
                results["cinematographer_analysis"] = CameraScriptAnalysis(**analysis) 
                if "script_title" in analysis:
                    results["script_title"] = analysis["script_title"]

        except HTTPException as e:
            print(f"Skipping role {role} due to error: {e.detail}")
            # Store the error message in the result payload
            results[f"{role}_analysis"] = {"error": e.detail}
        except Exception as e:
            print(f"An unexpected error occurred for role {role}: {e}")
            results[f"{role}_analysis"] = {"error": f"Internal processing error: {str(e)}"}

    # Return the aggregated result using the unified model
    return AllAnalysesResult(**results)

# --- Run Application ---
if __name__ == "__main__":
    import uvicorn
    # Start the server
    uvicorn.run(app, host="0.0.0.0", port=8000)