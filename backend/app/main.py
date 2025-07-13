from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator, Union
import json
import asyncio
import os
import uuid
from dotenv import load_dotenv

from .models import ChatRequest, ChatResponse
from .agents.smart_search_agent import SmartSearchAgent
from .agents.gemini_cli_agent import GeminiCLIAgent
from .agents.document_agent import DocumentAgent

load_dotenv()

app = FastAPI(title="DocBot API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Stream response using SSE format with document-based agent"""
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Use document agent for answers based on concatenated documentation
        agent = DocumentAgent(session_id=session_id)
        
        # Process query with documentation context
        async for result in agent.process_query(request.message):
            result['session_id'] = session_id
            yield f"data: {json.dumps(result)}\n\n"
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.05)
        
        yield f"data: {json.dumps({'type': 'done', 'content': '', 'session_id': session_id})}\n\n"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in stream_response: {error_details}")
        
        error_message = f"System error: {str(e)}"
            
        yield f"data: {json.dumps({'type': 'error', 'content': error_message, 'session_id': session_id})}\n\n"


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(
        stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/cli-chat")
async def cli_chat(request: ChatRequest):
    """Endpoint for CLI-style chat using document agent"""
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Use document agent for consistent responses
        agent = DocumentAgent(session_id)
        response = await agent.process_query_simple(request.message)
        
        return {
            "session_id": session_id,
            "response": response,
            "commands_executed": [],
            "outputs": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))