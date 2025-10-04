# main.py - FastAPI server with assistant integration

from fastapi import FastAPI, File, HTTPException, Depends, Header, BackgroundTasks, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from datetime import datetime

# Import the assistant components
from assistant.personal_assistant_integrated import (
    AssistantFactory, 
    PersonalAssistant
)

app = FastAPI(title="Production Assistant API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REQUEST/RESPONSE MODELS ====================

class AssistantInitRequest(BaseModel):
    user_id: str
    production_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    suggestions: List[str]
    provider: str
    timestamp: str

class ProactiveAlert(BaseModel):
    type: str
    priority: str
    message: str
    actions: List[str]

# ==================== AUTHENTICATION ====================

async def get_current_user(authorization: str = Header(None)) -> tuple:
    """
    Extract user_id and token from Authorization header
    Format: Bearer <token>
    
    In production, validate the token with your Spring Boot auth service
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        
        # TODO: Validate token with Spring Boot auth service
        # For now, decode JWT or call your Spring Boot /validate-token endpoint
        # Example:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         "http://your-spring-boot:8080/api/auth/validate",
        #         headers={"Authorization": authorization}
        #     )
        #     if response.status_code != 200:
        #         raise HTTPException(status_code=401, detail="Invalid token")
        #     user_data = response.json()
        #     return user_data['userId'], token
        
        # Placeholder: Extract user_id from token (implement proper JWT validation)
        user_id = "extracted_from_token"  # Replace with actual JWT decode
        
        return user_id, token
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

# ==================== ASSISTANT LIFECYCLE ENDPOINTS ====================

@app.post("/assistant/initialize")
async def initialize_assistant(
    request: AssistantInitRequest,
    user_auth: tuple = Depends(get_current_user)
):
    """
    Initialize personal assistant after user login
    This endpoint should be called by your Spring Boot backend after successful authentication
    """
    user_id, auth_token = user_auth
    
    # Verify user_id matches
    if user_id != request.user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
    
    try:
        # Create and initialize assistant
        assistant = await AssistantFactory.create_assistant(
            user_id=request.user_id,
            auth_token=auth_token,
            production_id=request.production_id
        )
        
        return {
            "status": "success",
            "message": f"Assistant initialized for {assistant.user_profile.get('name', 'user')}",
            "user_profile": {
                "name": assistant.user_profile.get('name'),
                "role": assistant.user_profile.get('role'),
                "department": assistant.user_profile.get('department')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize assistant: {str(e)}")

@app.post("/assistant/chat")
async def chat_with_assistant(
    request: ChatRequest,
    user_auth: tuple = Depends(get_current_user)
) -> ChatResponse:
    """
    Chat with personal assistant
    """
    user_id, _ = user_auth
    
    # Get assistant
    assistant = AssistantFactory.get_assistant(user_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not initialized. Call /initialize first")
    
    try:
        # Process message
        result = await assistant.chat(request.message)
        
        return ChatResponse(
            response=result['response'],
            suggestions=result['suggestions'],
            provider=result['provider'],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/assistant/proactive-check")
async def get_proactive_alerts(
    user_auth: tuple = Depends(get_current_user)
) -> List[ProactiveAlert]:
    """
    Get proactive alerts and reminders
    This endpoint can be polled periodically by the frontend (e.g., every 5 minutes)
    """
    user_id, _ = user_auth
    
    assistant = AssistantFactory.get_assistant(user_id)
    if not assistant:
        return []
    
    try:
        alerts = await assistant.proactive_check()
        return [ProactiveAlert(**alert) for alert in alerts]
    except Exception as e:
        print(f"Proactive check error: {e}")
        return []

@app.post("/assistant/toggle-proactive")
async def toggle_proactive_monitoring(
    enabled: bool,
    user_auth: tuple = Depends(get_current_user)
):
    """
    Enable/disable proactive monitoring
    """
    user_id, _ = user_auth
    
    assistant = AssistantFactory.get_assistant(user_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not initialized")
    
    assistant.proactive_enabled = enabled
    return {"status": "success", "proactive_enabled": enabled}

@app.delete("/assistant/session")
async def end_assistant_session(
    user_auth: tuple = Depends(get_current_user)
):
    """
    End assistant session (call on logout)
    """
    user_id, _ = user_auth
    
    await AssistantFactory.remove_assistant(user_id)
    return {"status": "success", "message": "Assistant session ended"}

# ==================== BACKGROUND TASKS ====================

async def proactive_monitoring_loop():
    """
    Background task that periodically checks all active assistants for proactive alerts
    Run this as a background task or separate worker
    """
    while True:
        try:
            # Check all active assistants
            for user_id, assistant in AssistantFactory._assistants.items():
                try:
                    alerts = await assistant.proactive_check()
                    
                    # If there are alerts, you could:
                    # 1. Send push notification via your notification service
                    # 2. Store in database for frontend to fetch
                    # 3. Send via WebSocket if you have one
                    
                    if alerts:
                        print(f"Proactive alerts for user {user_id}: {len(alerts)} alerts")
                        # TODO: Send alerts to user via your notification system
                except Exception as e:
                    print(f"Error in proactive check for {user_id}: {e}")
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
        
        # Wait 5 minutes before next check
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    """Start background monitoring on server startup"""
    # Start proactive monitoring in background
    asyncio.create_task(proactive_monitoring_loop())
    print("Background monitoring started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    await AssistantFactory.cleanup_all()
    print("All assistants cleaned up")

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_assistants": len(AssistantFactory._assistants),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/assistant/status")
async def get_assistant_status(user_auth: tuple = Depends(get_current_user)):
    """Get assistant status for current user"""
    user_id, _ = user_auth
    
    assistant = AssistantFactory.get_assistant(user_id)
    if not assistant:
        return {"initialized": False}
    
    return {
        "initialized": True,
        "user_name": assistant.user_profile.get('name'),
        "role": assistant.user_profile.get('role'),
        "production_id": assistant.production_id,
        "proactive_enabled": assistant.proactive_enabled,
        "llm_provider": assistant.llm_provider
    }

# ==================== EXAMPLE: Integration with your script analyzer ====================

# You can keep your existing script analyzer endpoints
# and add assistant integration there too

from your_script_analyzer import analyze_script_pdf  # Your existing code

@app.post("/analyze-script-with-assistant")
async def analyze_script_with_assistant_help(
    file: UploadFile = File(...),
    user_auth: tuple = Depends(get_current_user)
):
    """
    Analyze script and have assistant provide personalized insights
    """
    user_id, _ = user_auth
    
    # Run your existing script analysis
    analysis_result = await analyze_script_pdf(file)
    
    # Get assistant to provide personalized insights
    assistant = AssistantFactory.get_assistant(user_id)
    if assistant:
        # Ask assistant to summarize relevant parts based on user's role
        role = assistant.user_profile.get('role', 'Crew')
        
        summary_prompt = f"""Based on this script analysis, provide a brief summary 
        of the most relevant points for a {role}:
        
        {json.dumps(analysis_result, indent=2)[:2000]}  # First 2000 chars
        
        Keep it concise and actionable."""
        
        assistant_insights = await assistant.chat(summary_prompt)
        analysis_result['assistant_insights'] = assistant_insights['response']
    
    return analysis_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)