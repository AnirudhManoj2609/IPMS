import os
import re
import json
from io import BytesIO
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import PyPDF2
from groq import Groq

app = FastAPI(title="Script Analyzer AI", version="1.0.0")

client = Groq(api_key="KEYY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Character(BaseModel):
    name: str
    role: str
    description: str
    first_appearance_scene: int
    total_scenes: int
    suggested_casting_notes: str

class Location(BaseModel):
    name: str
    type: str
    scenes: List[int]
    total_scenes: int
    logistical_notes: str
    estimated_setup_complexity: str

class Prop(BaseModel):
    name: str
    category: str
    scenes: List[int]
    importance: str
    description: str

class SpecialRequirement(BaseModel):
    type: str
    description: str
    scenes: List[int]
    complexity: str
    estimated_cost_impact: str

class Scene(BaseModel):
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

class ScriptAnalysis(BaseModel):
    script_title: str
    total_pages: int
    total_scenes: int
    estimated_shoot_days: int
    estimated_budget_range: str
    scenes: List[Scene]
    characters: List[Character]
    locations: List[Location]
    props: List[Prop]
    special_requirements: List[SpecialRequirement]
    genre: str
    tone: str
    shooting_complexity: str
    key_challenges: List[str]
    budget_considerations: List[str]
    scheduling_recommendations: List[str]

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

def call_groq(prompt: str, max_tokens: int = 4000, temperature: float = 0.3) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content

def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from response that might be wrapped in markdown code blocks"""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return response_text

def analyze_script_with_groq(script_text: str, page_count: int) -> dict:
    prompt = f"""
Return ONLY a JSON matching this schema exactly. Do not wrap it in markdown code blocks:

{{
  "script_title": "string",
  "total_pages": 0,
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

Analyze this script and fill in all fields exactly as above. For the suggested_casting_notes field in each character, provide multiple suggestions (at least 2-3) of only Malayalam and other Indian actors who excel in similar roles, For characters under 18, suggest only actors who are close to the character’s age. 
Do not suggest adult actors. 
Include their age, experience, and IMDb ratings if possible based on their performances in recent movies (from the last 5-10 years), current trends, and stardom. Include references to their IMDb ratings for relevant films or overall, and explain why they fit the role. Format the notes as a bulleted list, e.g., '- Actor Name: Reason including recent movie examples and IMDb rating.'. Script:
{script_text}
"""
    response_text = call_groq(prompt)
    
    # Extract JSON from the response
    json_text = extract_json_from_response(response_text)
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse AI response as JSON: {str(e)}\nResponse preview: {response_text[:500]}"
        )

@app.get("/")
def root():
    return {"service": "Script Analyzer AI", "version": "1.0.0", "status": "online"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "ai_model": "llama-3.3-70b-versatile"}

@app.post("/analyze-script-pdf", response_model=ScriptAnalysis)
async def analyze_script_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    pdf_bytes = await file.read()
    script_text, page_count = extract_text_from_pdf(BytesIO(pdf_bytes))
    if len(script_text) < 100:
        raise HTTPException(status_code=400, detail="PDF content too short")
    analysis = analyze_script_with_groq(script_text, page_count)
    return ScriptAnalysis(**analysis)

@app.post("/analyze-script-text", response_model=ScriptAnalysis)
async def analyze_script_text(script_text: str):
    if len(script_text) < 100:
        raise HTTPException(status_code=400, detail="Script text too short")
    word_count = len(script_text.split())
    page_count = max(1, round(word_count / 250))
    analysis = analyze_script_with_groq(script_text, page_count)
    return ScriptAnalysis(**analysis)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
