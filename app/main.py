from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from fastapi.responses import StreamingResponse
import json

# Import chatbot engine
from core import app as chatbot_app
from langchain_core.messages import HumanMessage, AIMessage

# Initialize FastAPI app
api = FastAPI(title="Chatbot API", description="Financial Advisor Chatbot API", version="1.0.0")

# Enable CORS for Next.js frontend
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your Next.js frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  # will auto-generate if not given

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    thread_id: str

# Storage for sessions + history
conversation_configs = {}
conversation_history = {}

def get_thread_config(thread_id: str):
    """Get or create config for a specific thread"""
    if thread_id not in conversation_configs:
        conversation_configs[thread_id] = {"configurable": {"thread_id": thread_id}}
    return conversation_configs[thread_id]

def add_to_history(thread_id: str, role: str, content: str):
    if thread_id not in conversation_history:
        conversation_history[thread_id] = []
    conversation_history[thread_id].append(ChatMessage(
        role=role,
        content=content,
        timestamp=datetime.now()
    ))

@api.get("/")
async def root():
    return {"message": "Chatbot API is running", "status": "healthy"}

@api.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@api.post("/start-session")
async def start_session():
    """Create a new chat session (thread_id)."""
    session_id = str(uuid4())
    conversation_configs[session_id] = {"configurable": {"thread_id": session_id}}
    conversation_history[session_id] = []
    return {"thread_id": session_id}

@api.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Normal chat endpoint (non-streaming)."""
    try:
        thread_id = request.thread_id or str(uuid4())
        thread_config = get_thread_config(thread_id)

        # Enhance query based on keywords
        enhanced_query = request.message
        if any(keyword in request.message.lower() for keyword in ["runway", "burn", "cash", "expenses"]):
            enhanced_query += " Please also suggest specific actions I should consider."

        inputs = {"messages": [HumanMessage(content=enhanced_query)]}

        response_content = ""
        for msg, metadata in chatbot_app.stream(inputs, thread_config, stream_mode="messages"):
            if isinstance(msg, AIMessage) and msg.content:
                response_content += msg.content

        if not response_content:
            response_content = "I'm having trouble processing your request. Please try again."

        # Save history
        add_to_history(thread_id, "user", request.message)
        add_to_history(thread_id, "assistant", response_content)

        return ChatResponse(
            response=response_content,
            thread_id=thread_id,
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@api.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint for real-time responses."""
    async def generate_stream():
        try:
            thread_id = request.thread_id or str(uuid4())
            thread_config = get_thread_config(thread_id)

            enhanced_query = request.message
            if any(keyword in request.message.lower() for keyword in ["runway", "burn", "cash", "expenses"]):
                enhanced_query += " Please also suggest specific actions I should consider."

            inputs = {"messages": [HumanMessage(content=enhanced_query)]}

            # Save user message
            add_to_history(thread_id, "user", request.message)

            response_accumulated = ""
            for msg, metadata in chatbot_app.stream(inputs, thread_config, stream_mode="messages"):
                if isinstance(msg, AIMessage) and msg.content:
                    response_accumulated += msg.content
                    chunk = {
                        "content": msg.content,
                        "thread_id": thread_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Save assistant full response
            add_to_history(thread_id, "assistant", response_accumulated)

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            error_chunk = {
                "error": str(e),
                "thread_id": request.thread_id,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@api.get("/chat/history/{thread_id}", response_model=ChatHistoryResponse)
async def get_chat_history(thread_id: str):
    """Retrieve chat history for a session."""
    try:
        return ChatHistoryResponse(
            messages=conversation_history.get(thread_id, []),
            thread_id=thread_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@api.delete("/chat/history/{thread_id}")
async def clear_chat_history(thread_id: str):
    """Clear conversation history."""
    try:
        conversation_history.pop(thread_id, None)
        conversation_configs.pop(thread_id, None)
        return {"message": f"History cleared for thread {thread_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)
