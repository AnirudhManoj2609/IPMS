import os
import re
import json
from io import BytesIO
from typing import List, Union, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2
from groq import Groq

app = FastAPI(title="Script Analyzer AI", version="1.0.0")
client = Groq(api_key="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")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, 
                   allow_methods=["*"], allow_headers=["*"])

# Shared Utilities
def extract_text_from_pdf(pdf_file: BytesIO) -> tuple:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = "\n\n".join(p.extract_text() for p in pdf_reader.pages if p.extract_text())
    return text, len(pdf_reader.pages)

def call_groq(prompt: str, max_tokens: int = 8000) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def extract_json(text: str) -> str:
    match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.DOTALL)
    if match: return match.group(1)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

def chunk_text(text: str, words_per_chunk=1250):
    words = text.split()
    return [" ".join(words[i:i+words_per_chunk]) for i in range(0, len(words), words_per_chunk)]

# Enhanced Models
class BaseScene(BaseModel):
    scene_number: int
    scene_heading: str
    int_ext: str
    location: str
    time_of_day: str
    page_count: float
    description: str

class LocationDetails(BaseModel):
    name: str
    type: str
    scenes: List[int]
    total_scenes: int
    primary_recommendation: str
    recommendation_justification: str
    alternative_locations: List[dict]  # [{"name": "", "pros": "", "cons": "", "cost_difference": ""}]
    logistical_notes: str
    estimated_setup_complexity: str
    travel_distance_from_base_km: int
    travel_cost_estimate: str
    accessibility_notes: str
    permit_requirements: str

class BudgetBreakdown(BaseModel):
    category: str
    estimated_cost: str
    cost_range_min: int
    cost_range_max: int
    justification: str
    cost_drivers: List[str]
    potential_savings: List[str]

class DirectorScene(BaseScene):
    characters: List[str]
    props: List[str]
    special_requirements: List[str]
    estimated_setup_time_minutes: int
    estimated_shoot_time_minutes: int
    complexity_score: int
    location_budget_impact: str
    crew_meals_count: int
    transportation_needs: str

class DirectorAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    estimated_shoot_days: int
    estimated_budget_range: str
    budget_breakdown: List[BudgetBreakdown]
    total_predicted_budget: dict  # {"min": int, "max": int, "currency": "INR/USD"}
    scenes: List[DirectorScene]
    characters: List[dict]
    locations: List[LocationDetails]
    props: List[dict]
    special_requirements: List[dict]
    genre: str
    tone: str
    shooting_complexity: str
    key_challenges: List[str]
    budget_considerations: List[str]
    scheduling_recommendations: List[str]
    logistics_summary: dict  # {"total_travel_cost": "", "accommodation_nights": 0, "meal_budget": ""}

class CameraScene(BaseScene):
    total_shots_estimated: int
    primary_camera_positions: List[str]
    recommended_camera_package: str
    lighting_approach: str
    crew_size_recommendation: int
    gimbal_required: bool
    crane_dolly_required: bool
    drone_required: bool
    special_fps_required: str
    estimated_setup_time_minutes: int
    estimated_shoot_time_minutes: int
    technical_complexity_score: int
    post_production_requirements: dict  # {"editing_complexity": "", "vfx_shots": 0, "vfx_complexity": "", "color_grading_hours": 0, "vfx_percentage": 0}
    estimated_post_budget: str

class PostProductionBreakdown(BaseModel):
    category: str  # "Editing", "VFX", "Color Grading", "Sound Design"
    total_hours_estimated: int
    complexity_level: str
    estimated_cost: str
    percentage_of_total_post: int
    key_requirements: List[str]

class CameraAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    estimated_shoot_days: int
    overall_visual_style: str
    aspect_ratio_recommendation: str
    scenes: List[CameraScene]
    shots: List[dict]
    lighting_setups: List[dict]
    camera_equipment: dict
    overall_technical_complexity: str
    key_technical_challenges: List[str]
    equipment_rental_budget_estimate: str
    crew_recommendations: dict
    post_production_breakdown: List[PostProductionBreakdown]
    total_post_production_budget: str
    vfx_summary: dict  # {"total_vfx_shots": 0, "vfx_percentage_of_project": 0, "estimated_vfx_budget": ""}

class CostumeAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    characters: List[dict]
    scenes: List[dict]
    wardrobe_budget_estimate: str
    continuity_guidelines: List[str]

class AllAnalysesResult(BaseModel):
    script_title: str
    total_pages: int
    director_analysis: Optional[Union[DirectorAnalysis, dict]] = None
    cinematographer_analysis: Optional[Union[CameraAnalysis, dict]] = None
    costume_analysis: Optional[Union[CostumeAnalysis, dict]] = None

# Enhanced Prompts with Detailed Casting Instructions
DIRECTOR_PROMPT = """Expert film director & production manager: analyze for comprehensive production planning with detailed budgeting and location analysis. Return JSON only:

{{
  "script_title": "",
  "total_pages": {pages},
  "total_scenes": 0,
  "estimated_shoot_days": 0,
  "estimated_budget_range": "",
  "budget_breakdown": [
    {{
      "category": "Cast & Crew",
      "estimated_cost": "₹X - ₹Y",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "Detailed breakdown of why this cost",
      "cost_drivers": ["Lead actor fees", "Crew size", "Shoot duration"],
      "potential_savings": ["Use emerging actors", "Reduce crew overtime"]
    }},
    {{
      "category": "Locations & Permits",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": [],
      "potential_savings": []
    }},
    {{
      "category": "Equipment Rental",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": [],
      "potential_savings": []
    }},
    {{
      "category": "Transportation & Logistics",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": ["Distance to locations", "Vehicle rentals", "Fuel costs"],
      "potential_savings": []
    }},
    {{
      "category": "Accommodation",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "Based on crew size and shoot days",
      "cost_drivers": ["Hotel rates", "Number of nights", "Crew size"],
      "potential_savings": ["Negotiate bulk rates", "Local crew members"]
    }},
    {{
      "category": "Food & Catering",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "Per person per day costs × crew × days",
      "cost_drivers": ["Crew size", "Meal frequency", "Location remoteness"],
      "potential_savings": ["Local caterers", "Simplified menu"]
    }},
    {{
      "category": "Props & Set Dressing",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": [],
      "potential_savings": []
    }},
    {{
      "category": "Costumes & Makeup",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": [],
      "potential_savings": []
    }},
    {{
      "category": "Post-Production",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "",
      "cost_drivers": [],
      "potential_savings": []
    }},
    {{
      "category": "Contingency (10-15%)",
      "estimated_cost": "",
      "cost_range_min": 0,
      "cost_range_max": 0,
      "justification": "Buffer for unexpected costs",
      "cost_drivers": ["Weather delays", "Equipment issues"],
      "potential_savings": []
    }}
  ],
  "total_predicted_budget": {{
    "min": 0,
    "max": 0,
    "currency": "INR",
    "breakdown_by_phase": {{
      "pre_production": "₹X",
      "production": "₹Y",
      "post_production": "₹Z"
    }},
    "comparison_notes": "This budget is X% higher/lower than similar indie/commercial productions because..."
  }},
  "characters": [
    {{
      "name": "Character Name",
      "role": "Lead/Supporting/Minor",
      "description": "Detailed character description",
      "first_appearance_scene": 0,
      "total_scenes": 0,
      "suggested_casting_notes": "PROVIDE SPECIFIC ACTOR NAMES with detailed analysis in this format:\n\n- Fahadh Faasil (Age: 41): Perfect for complex characters requiring subtle intensity. Recent standout performances in 'Malik' (IMDb 7.9/10) and 'Joji' (IMDb 7.6/10) showcase his ability to portray morally ambiguous protagonists. His restrained acting style suits contemplative roles. National Award winner with consistent box office appeal in Malayalam cinema.\n\n- Dulquer Salmaan (Age: 38): Versatile actor excellent for charismatic leads. Recent successes include 'Kurup' (IMDb 7.2/10) and 'Sita Ramam' (IMDb 8.1/10). Strong pan-Indian appeal with proven track record in romantic and action genres. Commands higher fee but brings significant star power and youth appeal.\n\n- Tovino Thomas (Age: 35): Rising star perfect for action-oriented and intense roles. Recent blockbuster 'Minnal Murali' (IMDb 7.8/10) and '2018' (IMDb 8.0/10) demonstrate his range and physicality. More budget-friendly than established stars while delivering compelling performances. Strong social media presence appeals to younger demographics.\n\nNOTE: For characters under 18, ONLY suggest actors who are actually close to that age. Example for 15-year-old character:\n\n- Anaswara Rajan (Age: 20): Young actress who can convincingly portray teenage roles. Notable performance in 'Varane Avashyamund' (IMDb 7.1/10). Age-appropriate casting crucial for authenticity."
    }}
  ],
  "locations": [
    {{
      "name": "Beach Coastline",
      "type": "EXT",
      "scenes": [1, 5, 12],
      "total_scenes": 3,
      "primary_recommendation": "Kovalam Beach, Thiruvananthapuram",
      "recommendation_justification": "Less crowded than Varkala, better golden hour lighting, easier permit process, 45km from city base",
      "alternative_locations": [
        {{
          "name": "Varkala Beach",
          "pros": "Dramatic cliffs, more scenic",
          "cons": "Tourist heavy, harder crowd control, 30% more expensive permits",
          "cost_difference": "+₹50,000"
        }},
        {{
          "name": "Marari Beach",
          "pros": "Pristine, less crowded",
          "cons": "120km from base, higher travel costs, limited nearby facilities",
          "cost_difference": "+₹80,000 (travel & accommodation)"
        }}
      ],
      "logistical_notes": "Requires police permission, best shot during 6-9 AM or 4-6 PM",
      "estimated_setup_complexity": "Medium",
      "travel_distance_from_base_km": 45,
      "travel_cost_estimate": "₹15,000 (round trip for 3 days, 2 vehicles)",
      "accessibility_notes": "Good road access, parking available 200m from beach",
      "permit_requirements": "Tourism Department + Local Police NOC, ₹5,000"
    }}
  ],
  "props": [
    {{
      "name": "",
      "category": "",
      "scenes": [],
      "importance": "",
      "description": ""
    }}
  ],
  "special_requirements": [
    {{
      "type": "",
      "description": "",
      "scenes": [],
      "complexity": "",
      "estimated_cost_impact": ""
    }}
  ],
  "scenes": [
    {{
      "scene_number": 0,
      "scene_heading": "",
      "int_ext": "",
      "location": "",
      "time_of_day": "",
      "page_count": 0,
      "description": "",
      "characters": [],
      "props": [],
      "special_requirements": [],
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "complexity_score": 0,
      "location_budget_impact": "Low/Medium/High - explain why",
      "crew_meals_count": 0,
      "transportation_needs": "Local/Medium-distance/Remote"
    }}
  ],
  "genre": "",
  "tone": "",
  "shooting_complexity": "",
  "key_challenges": [],
  "budget_considerations": [
    "Compare this budget to similar Malayalam films",
    "Highlight cost-intensive elements",
    "Suggest budget optimization strategies"
  ],
  "scheduling_recommendations": [],
  "logistics_summary": {{
    "total_travel_cost": "₹X across all locations",
    "accommodation_nights": 0,
    "accommodation_cost": "₹Y",
    "meal_budget": "₹Z (crew size × days × ₹300 per person per day)",
    "total_logistics_cost": "₹A",
    "logistics_percentage_of_budget": "X%"
  }}
}}

CRITICAL CASTING INSTRUCTIONS:
1. For EACH character, provide AT LEAST 2-3 SPECIFIC Malayalam/Indian actor names (NOT generic descriptions)
2. For each suggested actor, include:
   - Actor's full name and current age
   - Recent film examples from last 5-10 years with IMDb ratings
   - Why they fit the role (acting style, previous similar roles, physical characteristics)
   - Awards, recognition, or box office track record
   - Fee range if relevant to budget considerations
3. For characters UNDER 18: ONLY suggest actors who are actually close to that age in real life
4. Format as bullet points with detailed explanations
5. Consider both star power vs budget constraints
6. Include mix of established stars, rising talents, and budget-friendly options

Example of CORRECT format:
"suggested_casting_notes": "- Parvathy Thiruvothu (Age: 36): National Award-winning actress ideal for emotionally complex female leads. Exceptional in 'Take Off' (IMDb 8.1/10) and 'Uyare' (IMDb 8.0/10). Known for choosing content-driven cinema. Fee: ₹40-60 lakhs.\n\n- Nimisha Sajayan (Age: 26): Rising star perfect for raw, authentic performances. Breakthrough role in 'The Great Indian Kitchen' (IMDb 8.3/10). More budget-friendly at ₹15-25 lakhs while delivering award-worthy performances."

IMPORTANT: 
- Calculate meal costs based on: crew size × shoot days × 3 meals × ₹300 per meal
- Calculate accommodation: crew size × nights × ₹1500 per night average
- Calculate travel: distance × fuel cost + vehicle rental
- Compare budget to similar regional productions
- Provide specific rupee amounts in final numbers
- ALWAYS give SPECIFIC actor names with detailed analysis, NEVER generic suggestions

Script: {script}"""

CAMERA_PROMPT = """Expert cinematographer: analyze with detailed post-production requirements. Return JSON only:

{{
  "script_title": "",
  "total_pages": {pages},
  "total_scenes": 0,
  "estimated_shoot_days": 0,
  "overall_visual_style": "",
  "cinematography_genre": "",
  "aspect_ratio_recommendation": "",
  "color_grading_approach": "",
  "reference_films": [],
  "scenes": [
    {{
      "scene_number": 0,
      "scene_heading": "",
      "int_ext": "",
      "location": "",
      "time_of_day": "",
      "page_count": 0,
      "description": "",
      "total_shots_estimated": 0,
      "primary_camera_positions": [],
      "recommended_camera_package": "",
      "lighting_approach": "",
      "power_requirements": "",
      "crew_size_recommendation": 0,
      "gimbal_required": false,
      "crane_dolly_required": false,
      "drone_required": false,
      "underwater_required": false,
      "special_fps_required": "",
      "color_temperature_notes": "",
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "technical_complexity_score": 0,
      "post_production_requirements": {{
        "editing_complexity": "Simple/Medium/Complex - explain why",
        "vfx_shots": 0,
        "vfx_complexity": "None/Basic/Medium/Complex - what type of VFX",
        "color_grading_hours": 0,
        "vfx_percentage": 0,
        "vfx_description": "Detailed list of VFX needed (wire removal, compositing, CGI elements, etc.)",
        "editing_notes": "Specific editing requirements (multicam, slow-mo, match cuts, etc.)"
      }},
      "estimated_post_budget": "₹X for this scene's post work"
    }}
  ],
  "shots": [
    {{
      "shot_number": "",
      "scene_number": 0,
      "shot_type": "",
      "shot_size": "",
      "camera_angle": "",
      "camera_movement": "",
      "lens_focal_length": "",
      "aperture_recommendation": "",
      "frame_rate": "",
      "stabilization_required": "",
      "special_equipment": [],
      "lighting_notes": "",
      "composition_notes": "",
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "technical_difficulty": "",
      "requires_vfx": false,
      "vfx_notes": ""
    }}
  ],
  "lighting_setups": [
    {{
      "scene_number": 0,
      "location": "",
      "time_of_day": "",
      "lighting_style": "",
      "key_lights": [],
      "fill_lights": [],
      "practical_lights": [],
      "modifiers_needed": [],
      "power_requirements": "",
      "setup_complexity": "",
      "estimated_setup_time_minutes": 0
    }}
  ],
  "camera_equipment": {{
    "camera_body": "",
    "lenses_required": [],
    "stabilization": [],
    "specialty_rigs": [],
    "filters_needed": [],
    "justification": ""
  }},
  "camera_movements": [
    {{
      "movement_type": "",
      "scenes": [],
      "total_occurrences": 0,
      "equipment_needed": "",
      "crew_expertise_level": "",
      "notes": ""
    }}
  ],
  "visual_effects": [
    {{
      "effect_type": "",
      "description": "",
      "scenes": [],
      "camera_requirements": "",
      "pre_production_notes": "",
      "on_set_requirements": "",
      "post_production_notes": "",
      "estimated_vfx_hours": 0,
      "estimated_vfx_cost": ""
    }}
  ],
  "post_production_breakdown": [
    {{
      "category": "Editing",
      "total_hours_estimated": 0,
      "complexity_level": "Basic/Intermediate/Advanced",
      "estimated_cost": "₹X (₹Y per hour × Z hours)",
      "percentage_of_total_post": 40,
      "key_requirements": ["Multi-cam editing", "Color correction", "Sound sync"]
    }},
    {{
      "category": "VFX",
      "total_hours_estimated": 0,
      "complexity_level": "",
      "estimated_cost": "",
      "percentage_of_total_post": 30,
      "key_requirements": ["List specific VFX shots", "Green screen compositing", "Object removal"]
    }},
    {{
      "category": "Color Grading",
      "total_hours_estimated": 0,
      "complexity_level": "",
      "estimated_cost": "",
      "percentage_of_total_post": 20,
      "key_requirements": ["Cinematic look development", "Shot matching", "Style consistency"]
    }},
    {{
      "category": "Sound Design & Mixing",
      "total_hours_estimated": 0,
      "complexity_level": "",
      "estimated_cost": "",
      "percentage_of_total_post": 10,
      "key_requirements": ["ADR sessions", "Foley recording", "5.1 mixing"]
    }}
  ],
  "total_post_production_budget": "₹X total for all post work",
  "vfx_summary": {{
    "total_vfx_shots": 0,
    "vfx_percentage_of_project": 0,
    "estimated_vfx_budget": "₹X",
    "vfx_breakdown": {{
      "compositing": "X shots, ₹Y",
      "cgi_elements": "X shots, ₹Y",
      "cleanup_removal": "X shots, ₹Y",
      "motion_graphics": "X shots, ₹Y"
    }},
    "vfx_timeline": "X weeks for completion"
  }},
  "overall_technical_complexity": "",
  "key_technical_challenges": [],
  "pre_production_requirements": [],
  "equipment_rental_budget_estimate": "",
  "crew_recommendations": {{}},
  "location_scouting_priorities": []
}}

IMPORTANT:
- For each scene, calculate VFX percentage (shots requiring VFX / total shots × 100)
- Estimate editing hours based on: basic scene = 4 hours, medium = 8 hours, complex = 16+ hours
- Estimate VFX hours per shot: simple = 4-8 hours, medium = 16-32 hours, complex = 40+ hours
- Calculate color grading: 2-4 hours per finished minute of footage
- Provide specific cost estimates for Kerala/Indian post-production rates

Script: {script}"""

COSTUME_PROMPT = """Expert costume designer: analyze wardrobe needs. Return JSON only:
{{"script_title":"","total_pages":{pages},"total_scenes":0,"characters":[{{"character_name":"",
"character_age":0,"character_role":"","style_notes":"","color_palette":"","costume_count":0,
"wardrobe_notes":"","special_requirements":[]}}],"scenes":[{{"scene_number":0,"characters":[],
"costume_changes":[],"special_conditions":[],"continuity_notes":"",
"estimated_costume_prep_time_minutes":0}}],"wardrobe_budget_estimate":"","continuity_guidelines":[],
"special_costume_considerations":[]}}
Script: {script}"""

def analyze_role(role: str, script: str, pages: int) -> dict:
    prompts = {
        "director": DIRECTOR_PROMPT,
        "cinematographer": CAMERA_PROMPT,
        "costume": COSTUME_PROMPT
    }
    prompt = prompts[role].format(pages=pages, script=script)
    response = call_groq(prompt, max_tokens=8000)
    return json.loads(extract_json(response))

@app.post("/analyze-script-pdf", response_model=AllAnalysesResult)
async def analyze_script_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "File must be PDF")
    
    script_text, page_count = extract_text_from_pdf(BytesIO(await file.read()))
    if len(script_text) < 100:
        raise HTTPException(400, "PDF too short")

    results = {"script_title": "Analysis In Progress", "total_pages": page_count}

    for role in ["director", "cinematographer", "costume"]:
        try:
            if role == "cinematographer":
                chunks = chunk_text(script_text)
                scenes, shots = [], []
                last = {}
                for chunk in chunks:
                    analysis = analyze_role(role, chunk, len(chunk.split())//250)
                    scenes.extend(analysis.get("scenes", []))
                    shots.extend(analysis.get("shots", []))
                    last = analysis
                analysis = {**last, "scenes": scenes, "shots": shots}
            else:
                analysis = analyze_role(role, script_text, page_count)
            
            model_map = {
                "director": DirectorAnalysis,
                "cinematographer": CameraAnalysis,
                "costume": CostumeAnalysis
            }
            results[f"{role}_analysis"] = model_map[role](**analysis)
            results["script_title"] = analysis.get("script_title", results["script_title"])
        except Exception as e:
            results[f"{role}_analysis"] = {"error": str(e)}

    return AllAnalysesResult(**results)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)