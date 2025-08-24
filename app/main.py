import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from fastapi.responses import StreamingResponse
import json
from tools import calculate_customer_churn, get_monthly_financial_data, get_monthly_financial_data_by_startup, get_onboarding_data, get_onboarding_data_by_startup
from db import get_connection
from core import app as chatbot_app
from logger import log_error
from langchain_core.messages import HumanMessage, AIMessage
import psycopg2.extras

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

# Models (keep existing models)
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

class DashboardRequest(BaseModel):
    startup_name: str

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
    try:
        session_id = str(uuid4())
        conversation_configs[session_id] = {"configurable": {"thread_id": session_id}}
        conversation_history[session_id] = []
        return {"thread_id": session_id}
    except Exception as e:
        log_error(
            error_type="SESSION_CREATION_ERROR",
            error_message=f"Failed to create session: {str(e)}",
            context={"endpoint": "/start-session"}
        )
        raise HTTPException(status_code=500, detail="Failed to create session")

@api.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Normal chat endpoint (non-streaming)."""
    thread_id = request.thread_id or str(uuid4())
    
    try:
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
            log_error(
                error_type="EMPTY_RESPONSE_ERROR",
                error_message="Chatbot returned empty response",
                context={"user_message": request.message, "enhanced_query": enhanced_query},
                thread_id=thread_id
            )
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
        log_error(
            error_type="CHAT_ENDPOINT_ERROR",
            error_message=f"Error in chat endpoint: {str(e)}",
            context={
                "user_message": request.message,
                "endpoint": "/chat"
            },
            thread_id=thread_id
        )
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@api.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint for real-time responses."""
    async def generate_stream():
        thread_id = request.thread_id or str(uuid4())
        
        try:
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
            log_error(
                error_type="STREAM_ENDPOINT_ERROR",
                error_message=f"Error in streaming endpoint: {str(e)}",
                context={
                    "user_message": request.message,
                    "endpoint": "/chat/stream"
                },
                thread_id=thread_id
            )
            error_chunk = {
                "error": str(e),
                "thread_id": thread_id,
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
        log_error(
            error_type="HISTORY_RETRIEVAL_ERROR",
            error_message=f"Error retrieving history: {str(e)}",
            context={"endpoint": "/chat/history"},
            thread_id=thread_id
        )
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@api.delete("/chat/history/{thread_id}")
async def clear_chat_history(thread_id: str):
    """Clear conversation history."""
    try:
        conversation_history.pop(thread_id, None)
        conversation_configs.pop(thread_id, None)
        return {"message": f"History cleared for thread {thread_id}"}
    except Exception as e:
        log_error(
            error_type="HISTORY_CLEAR_ERROR",
            error_message=f"Error clearing history: {str(e)}",
            context={"endpoint": "/chat/history (DELETE)"},
            thread_id=thread_id
        )
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@api.get("/db/{table_name}")
async def get_table_data(table_name: str, limit: int = 10):
    """Retrieve rows from a given database table."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT * FROM {table_name} LIMIT %s;", (limit,))
                colnames = [desc[0] for desc in cur.description] 
                rows = cur.fetchall()

        # Format rows into list of dicts
        results = [dict(zip(colnames, row)) for row in rows]
        return {"table": table_name, "rows": results}

    except Exception as e:
        log_error(
            error_type="RETRIEVE_DATA_ERROR",
            error_message=f"Error retrieving data: {str(e)}",
            context={"endpoint": "/db/table_name (GET)"},
        )
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)


# endpoints for dashboard 
@api.post("/db/overview")
def get_dashboard_overview(req: DashboardRequest):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                retObj = {}

                # current cash - FIXED: typo in column name and missing comma in tuple
                cur.execute("SELECT initial_cash FROM onboarding_data WHERE startup_name = %s LIMIT 1;", (req.startup_name,))
                rows = cur.fetchone()

                current_cash = float(rows['initial_cash'])  # FIXED: was 'intital_cash'

                # FIXED: Need to pass startup_name to get_monthly_financial_data
                monthly_data = get_monthly_financial_data_by_startup(req.startup_name)
    
                for month in monthly_data:
                    total_expenses = (month['product_dev_expenses'] + 
                                    month['manpower_expenses'] + 
                                    month['marketing_expenses'] + 
                                    month['operations_expenses'] + 
                                    month['other_expenses'])
                    
                    monthly_cash_flow = month['revenue'] - total_expenses
                    current_cash += monthly_cash_flow

                retObj['current_cash'] = current_cash

                # monthly burn - FIXED: removed f-string and added missing comma
                cur.execute("SELECT AVG(product_dev_expenses + manpower_expenses + operations_expenses + other_expenses + marketing_expenses) AS avg_monthly_burn FROM monthly_financial_data WHERE startup_name = %s;", (req.startup_name,))
                rows = cur.fetchone()

                retObj['monthly_burn'] = rows['avg_monthly_burn']

                # mrr - FIXED: removed f-string and added missing comma
                cur.execute("SELECT AVG(revenue) AS mrr FROM monthly_financial_data WHERE startup_name = %s;", (req.startup_name,))
                rows = cur.fetchone()

                retObj['mrr'] = rows['mrr']

                # runway - FIXED: Handle case where net_burn might be negative or zero
                recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
                if not recent_months:  # FIXED: Handle empty monthly_data
                    retObj['runway'] = float('inf')
                else:
                    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
                    avg_expenses = sum(month['product_dev_expenses'] + month['manpower_expenses'] + 
                                    month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses'] 
                                    for month in recent_months) / len(recent_months)
        
                    net_burn = avg_expenses - avg_revenue
                    
                    # FIXED: Handle negative net_burn (profitable) or zero burn
                    if net_burn <= 0:
                        retObj['runway'] = float('inf')  # Company is profitable or breaking even
                    else:
                        runway = math.floor(current_cash / net_burn)
                        retObj['runway'] = runway

                # arr
                retObj['arr'] = retObj['mrr'] * 12

                # ltv:cac - FIXED: Need to pass startup_name to get_onboarding_data
                onboarding = get_onboarding_data_by_startup(req.startup_name)
                churn_data = calculate_customer_churn(monthly_data, onboarding)

                # FIXED: Handle empty churn_data
                if not churn_data:
                    retObj['ltv'] = 0
                    retObj['cac'] = 0
                    retObj['payback_period'] = float('inf')
                else:
                    recent_churn_data = churn_data[-3:] if len(churn_data) >= 3 else churn_data
                    avg_monthly_churn_rate = sum(month['churn_rate'] for month in recent_churn_data) / len(recent_churn_data) / 100
                    avg_active_customers = sum(month['active_customers'] for month in recent_months) / len(recent_months)

                    arpu = avg_revenue / avg_active_customers if avg_active_customers > 0 else 0

                    customer_lifespan = (1 / avg_monthly_churn_rate) if avg_monthly_churn_rate > 0 else float('inf')
                    ltv = arpu * customer_lifespan if customer_lifespan != float('inf') else float('inf')
                    
                    retObj['ltv'] = ltv

                    # CAC calculation
                    recent_marketing = sum(month['marketing_expenses'] for month in recent_months)
                    recent_new_customers = sum(month['new_customers'] for month in recent_months)
                    recent_cac = (recent_marketing / recent_new_customers) if recent_new_customers > 0 else float('inf')

                    retObj['cac'] = recent_cac

                    # payback period
                    payback_period = (recent_cac / arpu) if arpu > 0 and recent_cac != float('inf') else float('inf')
                    retObj['payback_period'] = payback_period

                return retObj

    except Exception as e:
        log_error(
            error_type="RETRIEVE_DATA_ERROR",
            error_message=f"Error retrieving data: {str(e)}",
            context={"endpoint": "/db/overview (POST)"},  # FIXED: endpoint description
        )
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")