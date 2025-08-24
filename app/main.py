from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from fastapi.responses import StreamingResponse, JSONResponse
import json
from db import get_connection
from core import app as chatbot_app
from logger import log_error
from langchain_core.messages import HumanMessage, AIMessage
# Import the tools module to access startup context functions
from tools import set_startup_context, get_startup_name, get_onboarding_data,get_monthly_financial_data,calculate_customer_churn, calculate_current_cash, get_current_metrics

# Initialize FastAPI app
api = FastAPI(title="Chatbot API", description="Financial Advisor Chatbot API", version="1.0.0")

# Enable CORS for Next.js frontend
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your Next.js frontend URL
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Updated Models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  # will auto-generate if not given
    startup_name: Optional[str] = None  # NEW: Accept startup_name in chat requests

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    thread_id: str

# NEW: Startup context models
class StartupContextRequest(BaseModel):
    startup_name: str

class StartupContextResponse(BaseModel):
    startup_name: str
    message: str

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

# NEW: Startup context management endpoints
@api.post("/startup/context", response_model=StartupContextResponse)
async def set_startup_context_endpoint(request: StartupContextRequest):
    """Set the global startup context for all tools."""
    try:
        set_startup_context(request.startup_name)
        return StartupContextResponse(
            startup_name=request.startup_name,
            message=f"Startup context set to: {request.startup_name}"
        )
    except Exception as e:
        log_error(
            error_type="CONTEXT_SET_ERROR",
            error_message=f"Failed to set startup context: {str(e)}",
            context={"endpoint": "/startup/context", "startup_name": request.startup_name}
        )
        raise HTTPException(status_code=500, detail="Failed to set startup context")

@api.get("/startup/context")
async def get_startup_context_endpoint():
    """Get the current startup context."""
    try:
        current_startup = get_startup_name()
        return {
            "startup_name": current_startup,
            "message": f"Current startup context: {current_startup or 'Not set'}"
        }
    except Exception as e:
        log_error(
            error_type="CONTEXT_GET_ERROR",
            error_message=f"Failed to get startup context: {str(e)}",
            context={"endpoint": "/startup/context (GET)"}
        )
        raise HTTPException(status_code=500, detail="Failed to get startup context")

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
        # NEW: Set startup context if provided
        if request.startup_name:
            set_startup_context(request.startup_name)
            
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
                "startup_name": request.startup_name,
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
            # NEW: Set startup context if provided
            if request.startup_name:
                set_startup_context(request.startup_name)
                
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
                    "startup_name": request.startup_name,
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
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")\

@api.get("/cashflow")
async def get_cashflow_data():
    """
    Monthly cash flow analysis
    Returns: cash in (revenue), cash out (expenses), cash balance over time
    """
    try:
        startup_name = get_startup_name()
        if not startup_name:
            raise HTTPException(status_code=400, detail="No startup name set")
        
        onboarding = get_onboarding_data(startup_name)
        monthly_data = get_monthly_financial_data(startup_name)
        
        if not onboarding:
            raise HTTPException(status_code=404, detail="No onboarding data found")
        
        cashflow_data = []
        running_cash_balance = onboarding['initial_cash']
        
        # Initial month baseline
        cashflow_data.append({
            "month": onboarding['onboarding_date'].strftime('%Y-%m') if onboarding['onboarding_date'] else "Initial",
            "cash_in": 0,
            "cash_out": 0,
            "cash_balance": running_cash_balance,
            "net_flow": 0
        })
        
        # Process monthly data
        for month in monthly_data:
            cash_in = month['revenue']
            cash_out = (
                month['product_dev_expenses'] +
                month['manpower_expenses'] +
                month['marketing_expenses'] +
                month['operations_expenses'] +
                month['other_expenses']
            )
            net_flow = cash_in - cash_out
            running_cash_balance += net_flow
            
            cashflow_data.append({
                "month": month['date'].strftime('%Y-%m'), # y-axis
                "cash_in": cash_in,
                "cash_out": cash_out,
                "cash_balance": running_cash_balance, # x-axis
                "net_flow": net_flow
            })
        return {
            "data": cashflow_data,
            "summary": {
                "initial_cash": onboarding['initial_cash'],
                "current_balance": running_cash_balance,
                "total_months": len(cashflow_data) - 1
            }
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("API_ERROR", f"Error in /cashflow: {str(e)}", {"endpoint": "/cashflow"})
        raise HTTPException(status_code=500, detail="Internal server error")
    
@api.get("/revenue")
async def get_revenue_data():
    """
    Revenue analysis including MRR growth, churn, ARPU, and NRR
    """
    try:
        startup_name = get_startup_name()
        if not startup_name:
            raise HTTPException(status_code=400, detail="No startup context set")

        onboarding = get_onboarding_data(startup_name)
        monthly_data = get_monthly_financial_data(startup_name)

        if not onboarding or not monthly_data:
            raise HTTPException(status_code=404, detail="Insufficient data for revenue analysis")

        churn_data = calculate_customer_churn(monthly_data, onboarding)
        revenue_analysis = []

        for i, month in enumerate(monthly_data):
            # Growth
            if i == 0:
                mrr_growth_pct = 0
                mrr_growth_amount = 0
            else:
                prev_revenue = monthly_data[i-1]['revenue']
                mrr_growth_amount = month['revenue'] - prev_revenue
                mrr_growth_pct = (mrr_growth_amount / prev_revenue * 100) if prev_revenue > 0 else 0

            # Churn
            month_churn = churn_data[i] if i < len(churn_data) else None
            churn_rate = month_churn['churn_rate'] if month_churn else 0

            # ARPU
            arpu = month['revenue'] / month['active_customers'] if month['active_customers'] > 0 else 0

            # NRR
            if i == 0:
                nrr = 100
            else:
                starting_customers = monthly_data[i-1]['active_customers']
                if starting_customers > 0:
                    new_customer_revenue = month['new_customers'] * arpu if month_churn else 0
                    continuing_customer_revenue = month['revenue'] - new_customer_revenue
                    prev_continuing_revenue = monthly_data[i-1]['revenue']
                    nrr = (continuing_customer_revenue / prev_continuing_revenue * 100) if prev_continuing_revenue > 0 else 100
                else:
                    nrr = 100

            revenue_analysis.append({
                "month": month['date'].strftime('%Y-%m'),
                "revenue": month['revenue'],
                "mrr_growth_amount": mrr_growth_amount,
                "mrr_growth_pct": mrr_growth_pct,
                "churn_rate": churn_rate,
                "arpu": arpu,
                "nrr": nrr,
                "active_customers": month['active_customers'],
                "new_customers": month['new_customers']
            })

         # 3-month summary lang if ever need mo
        recent_months = revenue_analysis[-3:] if len(revenue_analysis) >= 3 else revenue_analysis
        avg_mrr_growth = sum(m['mrr_growth_pct'] for m in recent_months) / len(recent_months)
        avg_churn = sum(m['churn_rate'] for m in recent_months) / len(recent_months)
        avg_arpu = sum(m['arpu'] for m in recent_months) / len(recent_months)
        avg_nrr = sum(m['nrr'] for m in recent_months) / len(recent_months)

        return {
            "data": revenue_analysis,
            "summary": {
                "avg_mrr_growth_pct": avg_mrr_growth,
                "avg_churn_rate": avg_churn,
                "avg_arpu": avg_arpu,
                "avg_nrr": avg_nrr,
                "total_months": len(revenue_analysis)
            }
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        log_error("API_ERROR", f"Error in /revenue: {str(e)}", {"endpoint": "/revenue"})
        raise HTTPException(status_code=500, detail="Internal server error")
    
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)