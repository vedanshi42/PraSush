import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from app.config import HOST, PORT, IS_SANDBOX_MODE
from app.models import GuidanceRequest, GuidanceResponse, ChatResponse
from app.services.memory_service import memory_manager
from app.services.ai_service import call_vision_model, call_reasoning_model, get_sandbox_response

app = FastAPI(
    title="PraSush Backend",
    description="FastAPI REST Backend for PraSush AI Visual Guidance Assistant",
    version="1.0.0"
)

# CORS configuration to allow local mobile and web connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    return {
        "status": "ok",
        "sandbox_mode": IS_SANDBOX_MODE,
        "message": "PraSush backend is active and running."
    }

@app.post("/api/clear_memory")
async def clear_memory(payload: Dict[str, str]) -> Dict[str, Any]:
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    memory_manager.clear_session(session_id)
    return {"status": "success", "message": f"Memory cleared for session: {session_id}"}

@app.post("/api/chat", response_model=GuidanceResponse)
async def process_chat(request: GuidanceRequest):
    try:
        session_id = request.session_id
        query = request.query.strip()
        image_data = request.image_data
        user_name = request.user_name
        mode = request.mode
        
        if not query:
            raise HTTPException(status_code=400, detail="Query text is required.")

        # Get rolling memory context
        history_context = memory_manager.get_formatted_context(session_id)
        
        # Determine if we should analyze an image
        image_description = None
        if image_data:
            if IS_SANDBOX_MODE:
                # In sandbox mode, we simulate image interpretation
                image_description = f"[Sandbox Image Captured: User captured an object for {mode} guidance]"
            else:
                try:
                    # Clean potential data URI header from base64 string
                    if "," in image_data:
                        image_data = image_data.split(",", 1)[1]
                    
                    # Call vision model (Phi-4) to describe the scene
                    image_description = call_vision_model(image_data, query)
                except Exception as ve:
                    print(f"Vision analysis failed, falling back to reasoning only. Error: {ve}")
                    image_description = "[Vision model analysis failed due to key/network, reasoning fallback]"

        # Call reasoning model (Llama-3.1) or Sandbox fallback
        if IS_SANDBOX_MODE:
            response_payload = get_sandbox_response(query, mode, image_data is not None, user_name)
        else:
            response_payload = call_reasoning_model(
                query=query,
                mode=mode,
                image_description=image_description,
                history_context=history_context,
                user_name=user_name
            )

        # Save context to memory
        memory_manager.add_user_message(session_id, query)
        memory_manager.add_assistant_message(session_id, response_payload.spoken_response)

        return response_payload

    except Exception as e:
        print(f"Internal server error: {e}")
        # Standard robust fallback instead of 500 error, so mobile app never crashes
        return get_sandbox_response(request.query, request.mode, request.image_data is not None, request.user_name)

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
