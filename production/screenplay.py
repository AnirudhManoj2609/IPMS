import os
import re
import json
from io import BytesIO
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import PyPDF2
from groq import Groq

app = FastAPI(title="Script Analyzer AI with Screenplay Generator", version="2.0.0")

client = Groq(api_key="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")

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

class ScreenplayScene(BaseModel):
    scene_number: int
    screenplay_text: str
    formatting_notes: str

class ScreenplayOutput(BaseModel):
    title: str
    scenes: List[ScreenplayScene]
    total_pages_estimated: int
    format_style: str

class ScreenplayRequest(BaseModel):
    scene_numbers: Optional[List[int]] = None
    style: str = "standard"

# ============= ORIGINAL SCRIPT ANALYZER FUNCTIONS =============

def extract_text_from_pdf(pdf_file: BytesIO) -> (List[str], int):
    """Extract text from PDF and return list of page texts"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pages = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return pages, len(pages)

def chunk_pages(pages: List[str], pages_per_chunk: int = 5) -> List[Dict[str, Any]]:
    """Split pages into chunks of specified size"""
    chunks = []
    for i in range(0, len(pages), pages_per_chunk):
        chunk_pages = pages[i:i + pages_per_chunk]
        chunk_text = "\n\n".join(chunk_pages)
        chunks.append({
            "text": chunk_text,
            "start_page": i + 1,
            "end_page": min(i + pages_per_chunk, len(pages)),
            "page_count": len(chunk_pages)
        })
    return chunks

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
    json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return response_text

def analyze_chunk(chunk: Dict[str, Any], chunk_index: int, total_chunks: int) -> dict:
    """Analyze a single chunk of the script"""
    prompt = f"""
You are analyzing chunk {chunk_index + 1} of {total_chunks} (pages {chunk['start_page']}-{chunk['end_page']}) of a film script.

Return ONLY valid JSON with this structure:

{{
  "scenes": [
    {{
      "scene_number": 0,
      "scene_heading": "string",
      "int_ext": "INT/EXT",
      "location": "string",
      "time_of_day": "string",
      "page_count": 0.0,
      "description": "string",
      "characters": ["string"],
      "props": ["string"],
      "special_requirements": ["string"],
      "estimated_setup_time_minutes": 0,
      "estimated_shoot_time_minutes": 0,
      "complexity_score": 0
    }}
  ],
  "characters_found": ["character_name"],
  "locations_found": ["location_name"],
  "props_found": ["prop_name"],
  "special_requirements_found": ["requirement_description"]
}}

Extract all scenes, characters, locations, props, and special requirements from this chunk.

Script chunk:
{chunk['text']}
"""
    
    response_text = call_groq(prompt, max_tokens=3000)
    json_text = extract_json_from_response(response_text)
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {
            "scenes": [],
            "characters_found": [],
            "locations_found": [],
            "props_found": [],
            "special_requirements_found": []
        }

def synthesize_analysis(chunk_analyses: List[dict], total_pages: int, script_preview: str) -> dict:
    """Combine chunk analyses into final comprehensive analysis"""
    
    all_characters = set()
    all_locations = set()
    all_props = set()
    all_requirements = set()
    all_scenes = []
    
    for chunk_analysis in chunk_analyses:
        all_characters.update(chunk_analysis.get("characters_found", []))
        all_locations.update(chunk_analysis.get("locations_found", []))
        all_props.update(chunk_analysis.get("props_found", []))
        all_requirements.update(chunk_analysis.get("special_requirements_found", []))
        all_scenes.extend(chunk_analysis.get("scenes", []))
    
    prompt = f"""
Based on the analyzed script data, create a comprehensive production analysis.

Total Pages: {total_pages}
Total Scenes: {len(all_scenes)}
Characters Found: {', '.join(list(all_characters)[:20])}
Locations Found: {', '.join(list(all_locations)[:20])}

Script Preview (first 1000 chars):
{script_preview[:1000]}

Return ONLY valid JSON matching this exact schema:

{{
  "script_title": "string",
  "total_pages": {total_pages},
  "total_scenes": {len(all_scenes)},
  "estimated_shoot_days": 0,
  "estimated_budget_range": "string",
  "characters": [
    {{
      "name": "string",
      "role": "string",
      "description": "string",
      "first_appearance_scene": 1,
      "total_scenes": 0,
      "suggested_casting_notes": "string"
    }}
  ],
  "locations": [
    {{
      "name": "string",
      "type": "INT/EXT",
      "scenes": [1],
      "total_scenes": 0,
      "logistical_notes": "string",
      "estimated_setup_complexity": "Low"
    }}
  ],
  "props": [
    {{
      "name": "string",
      "category": "string",
      "scenes": [1],
      "importance": "Medium",
      "description": "string"
    }}
  ],
  "special_requirements": [
    {{
      "type": "string",
      "description": "string",
      "scenes": [1],
      "complexity": "Medium",
      "estimated_cost_impact": "Medium"
    }}
  ],
  "genre": "string",
  "tone": "string",
  "shooting_complexity": "Medium",
  "key_challenges": ["string"],
  "budget_considerations": ["string"],
  "scheduling_recommendations": ["string"]
}}

For casting notes: Suggest only Malayalam and Indian actors. For characters under 18, suggest only age-appropriate actors. Include recent work (2015-2024), IMDb ratings, and why they fit. Format as bullet points.

Generate comprehensive metadata but keep scenes list from chunk analysis.
"""
    
    response_text = call_groq(prompt, max_tokens=4000)
    json_text = extract_json_from_response(response_text)
    
    try:
        synthesis = json.loads(json_text)
        synthesis["scenes"] = all_scenes
        return synthesis
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to synthesize analysis: {str(e)}"
        )

def analyze_script_with_groq(pages: List[str], page_count: int) -> dict:
    """Main analysis function that handles chunking and synthesis"""
    
    chunks = chunk_pages(pages, pages_per_chunk=5)
    
    print(f"Processing {len(chunks)} chunks...")
    
    chunk_analyses = []
    for i, chunk in enumerate(chunks):
        print(f"Analyzing chunk {i+1}/{len(chunks)}...")
        analysis = analyze_chunk(chunk, i, len(chunks))
        chunk_analyses.append(analysis)
    
    script_preview = "\n\n".join(pages[:2])  
    
    print("Synthesizing final analysis...")
    final_analysis = synthesize_analysis(chunk_analyses, page_count, script_preview)
    
    return final_analysis

# ============= SCREENPLAY GENERATOR FUNCTIONS =============

def generate_screenplay_scene(
    scene: Scene, 
    characters: List[Character],
    style: str = "standard"
) -> str:
    """Generate a fully formatted screenplay scene using AI"""
    
    char_info = []
    for char_name in scene.characters:
        char = next((c for c in characters if c.name.lower() == char_name.lower()), None)
        if char:
            char_info.append(f"{char.name}: {char.role} - {char.description}")
    
    char_context = "\n".join(char_info) if char_info else "Characters present in scene"
    
    prompt = f"""You are a professional screenwriter. Generate a complete screenplay scene in standard Hollywood format.

SCENE INFORMATION:
Scene Number: {scene.scene_number}
Scene Heading: {scene.int_ext}. {scene.location} - {scene.time_of_day}
Description: {scene.description}
Characters: {', '.join(scene.characters)}
Props: {', '.join(scene.props) if scene.props else 'None specified'}
Special Requirements: {', '.join(scene.special_requirements) if scene.special_requirements else 'None'}

CHARACTER DETAILS:
{char_context}

SCREENPLAY FORMAT RULES:
1. Scene heading in ALL CAPS: INT./EXT. LOCATION - TIME
2. Action lines in present tense, single-spaced
3. Character names CENTERED and IN CAPS before dialogue
4. Dialogue below character name, centered
5. Parentheticals in (lowercase) when needed for tone/action
6. Use proper spacing between elements

Generate a complete scene with:
- Vivid action description
- Natural, character-appropriate dialogue
- Proper scene flow and pacing
- Include props and special requirements organically
- Make it approximately {scene.page_count} pages worth of content

Write ONLY the formatted screenplay scene. Do not include explanations or meta-commentary.

SCREENPLAY SCENE:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000
    )
    
    return response.choices[0].message.content.strip()

def generate_complete_screenplay(
    analysis: ScriptAnalysis,
    scene_numbers: Optional[List[int]] = None,
    style: str = "standard"
) -> ScreenplayOutput:
    """Generate complete screenplay from ScriptAnalysis"""
    
    scenes = analysis.scenes
    
    if scene_numbers:
        scenes = [s for s in scenes if s.scene_number in scene_numbers]
    
    screenplay_scenes = []
    
    print(f"Generating screenplay for {len(scenes)} scenes...")
    
    for i, scene in enumerate(scenes, 1):
        print(f"Writing scene {i}/{len(scenes)} (Scene #{scene.scene_number})...")
        
        screenplay_text = generate_screenplay_scene(scene, analysis.characters, style)
        
        formatting_notes = f"Estimated page count: {scene.page_count}, "
        formatting_notes += f"Characters: {len(scene.characters)}, "
        formatting_notes += f"Complexity: {scene.complexity_score}/10"
        
        screenplay_scenes.append(ScreenplayScene(
            scene_number=scene.scene_number,
            screenplay_text=screenplay_text,
            formatting_notes=formatting_notes
        ))
    
    total_pages = sum(s.page_count for s in scenes)
    
    return ScreenplayOutput(
        title=analysis.script_title,
        scenes=screenplay_scenes,
        total_pages_estimated=int(total_pages),
        format_style=style
    )

def export_screenplay_to_text(screenplay: ScreenplayOutput) -> str:
    """Export screenplay to plain text format"""
    
    output = []
    output.append("=" * 60)
    output.append(screenplay.title.upper().center(60))
    output.append("=" * 60)
    output.append("\n\n")
    
    for scene in screenplay.scenes:
        output.append(scene.screenplay_text)
        output.append("\n\n")
        output.append("-" * 60)
        output.append("\n\n")
    
    output.append("\n")
    output.append(f"END OF SCREENPLAY")
    output.append(f"\nEstimated Total Pages: {screenplay.total_pages_estimated}")
    output.append(f"\nTotal Scenes: {len(screenplay.scenes)}")
    
    return "\n".join(output)

def export_screenplay_to_fountain(screenplay: ScreenplayOutput) -> str:
    """Export screenplay to Fountain format"""
    
    output = []
    output.append(f"Title: {screenplay.title}")
    output.append(f"Format: {screenplay.format_style}")
    output.append(f"Estimated Pages: {screenplay.total_pages_estimated}")
    output.append("\n===\n")
    
    for scene in screenplay.scenes:
        output.append(scene.screenplay_text)
        output.append("\n\n")
    
    return "\n".join(output)

# ============= API ENDPOINTS =============

@app.get("/")
def root():
    return {
        "service": "Script Analyzer AI with Screenplay Generator", 
        "version": "2.0.0", 
        "status": "online",
        "endpoints": {
            "analyze": ["/analyze-script-pdf", "/analyze-script-text"],
            "generate": ["/generate-screenplay", "/generate-screenplay-text", "/generate-screenplay-fountain"]
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "ai_model": "llama-3.3-70b-versatile", "features": ["analysis", "screenplay_generation"]}

@app.post("/analyze-script-pdf", response_model=ScriptAnalysis)
async def analyze_script_pdf(file: UploadFile = File(...)):
    """Analyze a PDF script and extract production details"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    pdf_bytes = await file.read()
    pages, page_count = extract_text_from_pdf(BytesIO(pdf_bytes))
    
    if page_count == 0 or sum(len(p) for p in pages) < 100:
        raise HTTPException(status_code=400, detail="PDF content too short or empty")
    
    analysis = analyze_script_with_groq(pages, page_count)
    return ScriptAnalysis(**analysis)

@app.post("/analyze-script-text", response_model=ScriptAnalysis)
async def analyze_script_text(script_text: str):
    """Analyze a text script and extract production details"""
    if len(script_text) < 100:
        raise HTTPException(status_code=400, detail="Script text too short")
    
    words = script_text.split()
    pages = []
    for i in range(0, len(words), 250):
        page_text = " ".join(words[i:i+250])
        pages.append(page_text)
    
    page_count = len(pages)
    analysis = analyze_script_with_groq(pages, page_count)
    return ScriptAnalysis(**analysis)

@app.post("/generate-screenplay", response_model=ScreenplayOutput)
async def generate_screenplay(analysis: ScriptAnalysis, request: ScreenplayRequest = ScreenplayRequest()):
    """Generate a formatted screenplay from analyzed script data"""
    try:
        screenplay = generate_complete_screenplay(
            analysis=analysis,
            scene_numbers=request.scene_numbers,
            style=request.style
        )
        return screenplay
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenplay generation failed: {str(e)}")

@app.post("/generate-screenplay-text", response_class=PlainTextResponse)
async def generate_screenplay_text(analysis: ScriptAnalysis, request: ScreenplayRequest = ScreenplayRequest()):
    """Generate and export screenplay as plain text"""
    try:
        screenplay = generate_complete_screenplay(
            analysis=analysis,
            scene_numbers=request.scene_numbers,
            style=request.style
        )
        return export_screenplay_to_text(screenplay)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenplay generation failed: {str(e)}")

@app.post("/generate-screenplay-fountain", response_class=PlainTextResponse)
async def generate_screenplay_fountain(analysis: ScriptAnalysis, request: ScreenplayRequest = ScreenplayRequest()):
    """Generate and export screenplay in Fountain format"""
    try:
        screenplay = generate_complete_screenplay(
            analysis=analysis,
            scene_numbers=request.scene_numbers,
            style=request.style
        )
        return export_screenplay_to_fountain(screenplay)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screenplay generation failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)