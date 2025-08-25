import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import uuid4
from fastapi.responses import StreamingResponse, JSONResponse
import json
from tools import (
    calculate_customer_churn, 
    get_monthly_financial_data, 
    get_onboarding_data, 
    calculate_current_cash
)
from db import get_connection
from core import create_chatbot_app
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
    startup_name: str  # REQUIRED: startup name for context

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessage]
    thread_id: str

class DashboardRequest(BaseModel):
    startup_name: str

# Storage for sessions + history (per thread_id)
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
    
    # Validate startup_name is provided
    if not request.startup_name:
        raise HTTPException(status_code=400, detail="startup_name is required")
    
    try:
        # Create chatbot app instance with startup context
        chatbot_app = create_chatbot_app(request.startup_name)
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
        
        # Validate startup_name is provided
        if not request.startup_name:
            error_chunk = {
                "error": "startup_name is required",
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            return
        
        try:
            # Create chatbot app instance with startup context
            chatbot_app = create_chatbot_app(request.startup_name)
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

@api.post("/db/cashflow")
async def get_cashflow_data(req: DashboardRequest):
    """
    Monthly cash flow analysis for a specific startup
    Returns: cash in (revenue), cash out (expenses), cash balance over time
    """
    try:
        onboarding = get_onboarding_data(req.startup_name)
        monthly_data = get_monthly_financial_data(req.startup_name)
        
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
                "month": month['date'].strftime('%Y-%m'),
                "cash_in": cash_in,
                "cash_out": cash_out,
                "cash_balance": running_cash_balance,
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
    
@api.post("/db/revenue")
async def get_revenue_data(req: DashboardRequest):
    """
    Revenue analysis including MRR growth, churn, ARPU, and NRR for a specific startup
    """
    try:
        onboarding = get_onboarding_data(req.startup_name)
        monthly_data = get_monthly_financial_data(req.startup_name)

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

         # 3-month summary
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

# Dashboard endpoint for dashboard overview
@api.post("/db/overview")
def get_dashboard_overview(req: DashboardRequest):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                retObj = {}

                # current cash - Get initial cash
                cur.execute("SELECT initial_cash FROM onboarding_data WHERE startup_name = %s LIMIT 1;", (req.startup_name,))
                rows = cur.fetchone()

                if not rows:
                    raise HTTPException(status_code=404, detail="No onboarding data found for startup")

                current_cash = float(rows['initial_cash'])

                # Calculate current cash by adding monthly cash flows
                monthly_data = get_monthly_financial_data(req.startup_name)
    
                for month in monthly_data:
                    total_expenses = (month['product_dev_expenses'] + 
                                    month['manpower_expenses'] + 
                                    month['marketing_expenses'] + 
                                    month['operations_expenses'] + 
                                    month['other_expenses'])
                    
                    monthly_cash_flow = month['revenue'] - total_expenses
                    current_cash += monthly_cash_flow

                retObj['current_cash'] = current_cash

                # monthly burn
                cur.execute("SELECT AVG(product_dev_expenses + manpower_expenses + operations_expenses + other_expenses + marketing_expenses) AS avg_monthly_burn FROM monthly_financial_data WHERE startup_name = %s;", (req.startup_name,))
                rows = cur.fetchone()

                retObj['monthly_burn'] = float(rows['avg_monthly_burn']) if rows['avg_monthly_burn'] else 0

                # mrr
                cur.execute("SELECT AVG(revenue) AS mrr FROM monthly_financial_data WHERE startup_name = %s;", (req.startup_name,))
                rows = cur.fetchone()

                retObj['mrr'] = float(rows['mrr']) if rows['mrr'] else 0

                # runway - Handle case where net_burn might be negative or zero
                recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
                if not recent_months:  # Handle empty monthly_data
                    retObj['runway'] = float('inf')
                else:
                    avg_revenue = sum(month['revenue'] for month in recent_months) / len(recent_months)
                    avg_expenses = sum(month['product_dev_expenses'] + month['manpower_expenses'] + 
                                    month['marketing_expenses'] + month['operations_expenses'] + month['other_expenses'] 
                                    for month in recent_months) / len(recent_months)
        
                    net_burn = avg_expenses - avg_revenue
                    
                    # Handle negative net_burn (profitable) or zero burn
                    if net_burn <= 0:
                        retObj['runway'] = float('inf')  # Company is profitable or breaking even
                    else:
                        runway = math.floor(current_cash / net_burn)
                        retObj['runway'] = runway

                # arr
                retObj['arr'] = retObj['mrr'] * 12

                # ltv:cac
                onboarding = get_onboarding_data(req.startup_name)
                churn_data = calculate_customer_churn(monthly_data, onboarding)

                # Handle empty churn_data
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
            context={"endpoint": "/db/overview (POST)"},
        )
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    
@api.post("/db/expenses")
async def get_expenses_data(req: DashboardRequest):
    """
    Expense breakdown showing each category as percentage of total
    """
    try:
        onboarding = get_onboarding_data(req.startup_name)
        monthly_data = get_monthly_financial_data(req.startup_name)

        if not onboarding or not monthly_data:
            raise HTTPException(status_code=404, detail="Insufficient data for revenue analysis")


        expenses_data = []
        for month in monthly_data:
            total_expenses = (
                month['product_dev_expenses'] +
                month['manpower_expenses'] +
                month['marketing_expenses'] +
                month['operations_expenses'] +
                month['other_expenses']
            )

            # Percentages
            if total_expenses > 0:
                product_dev_pct = (month['product_dev_expenses'] / total_expenses) * 100
                manpower_pct = (month['manpower_expenses'] / total_expenses) * 100
                marketing_pct = (month['marketing_expenses'] / total_expenses) * 100
                operations_pct = (month['operations_expenses'] / total_expenses) * 100
                other_pct = (month['other_expenses'] / total_expenses) * 100
            else:
                product_dev_pct = manpower_pct = marketing_pct = operations_pct = other_pct = 0

            expenses_data.append({
                "month": month['date'].strftime('%Y-%m'),
                "total_expenses": total_expenses,
                "product_dev_amount": month['product_dev_expenses'],
                "product_dev_pct": product_dev_pct,
                "manpower_amount": month['manpower_expenses'],
                "manpower_pct": manpower_pct,
                "marketing_amount": month['marketing_expenses'],
                "marketing_pct": marketing_pct,
                "operations_amount": month['operations_expenses'],
                "operations_pct": operations_pct,
                "other_amount": month['other_expenses'],
                "other_pct": other_pct
            })

        recent_months = expenses_data[-3:] if len(expenses_data) >= 3 else expenses_data
        avg_breakdown = {
            "product_dev_pct": sum(m['product_dev_pct'] for m in recent_months) / len(recent_months),
            "manpower_pct": sum(m['manpower_pct'] for m in recent_months) / len(recent_months),
            "marketing_pct": sum(m['marketing_pct'] for m in recent_months) / len(recent_months),
            "operations_pct": sum(m['operations_pct'] for m in recent_months) / len(recent_months),
            "other_pct": sum(m['other_pct'] for m in recent_months) / len(recent_months),
            "total_avg_expenses": sum(m['total_expenses'] for m in recent_months) / len(recent_months)
        }

        return {
            "data": expenses_data,
            "summary": avg_breakdown
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("API_ERROR", f"Error in /api/expenses: {str(e)}", {"endpoint": "/api/expenses"})
        raise HTTPException(status_code=500, detail="Internal server error")
    
@api.post("/db/runway")
async def get_runway_data(req: DashboardRequest):
    """
    Runway projections with current, optimistic, and pessimistic scenarios
    """
    try:
        onboarding = get_onboarding_data(req.startup_name)
        monthly_data = get_monthly_financial_data(req.startup_name)
        current_cash, month_elapsed = calculate_current_cash(req.startup_name)

        if not onboarding or not monthly_data or not current_cash:
            raise HTTPException(status_code=404, detail="Insufficient data for runway analysis")

        # Calculate averages
        if monthly_data:
            recent_months = monthly_data[-3:] if len(monthly_data) >= 3 else monthly_data
            avg_revenue = sum(m['revenue'] for m in recent_months) / len(recent_months)
            avg_expenses = sum(
                m['product_dev_expenses'] + m['manpower_expenses'] +
                m['marketing_expenses'] + m['operations_expenses'] + m['other_expenses']
                for m in recent_months
            ) / len(recent_months)
        else:
            avg_revenue = onboarding['target_revenue']
            avg_expenses = (
                onboarding['planned_product_dev'] + onboarding['planned_manpower'] +
                onboarding['planned_marketing'] + onboarding['planned_operations']
            )

        # Calculate scenario parameters
        current_net_flow = avg_revenue - avg_expenses
        optimistic_revenue = avg_revenue * 1.3
        optimistic_net_flow = optimistic_revenue - avg_expenses
        pessimistic_expenses = avg_expenses * 1.2
        pessimistic_net_flow = avg_revenue - pessimistic_expenses

        # Calculate runway months for each scenario
        current_runway_months = float('inf') if current_net_flow >= 0 else math.floor(current_cash / abs(current_net_flow))
        optimistic_runway_months = float('inf') if optimistic_net_flow >= 0 else math.floor(current_cash / abs(optimistic_net_flow))
        pessimistic_runway_months = float('inf') if pessimistic_net_flow >= 0 else math.floor(current_cash / abs(pessimistic_net_flow))

        # Generate monthly projections
        projection_months = 24
        runway_projections = []
        
        for month in range(1, projection_months + 1):
            # Calculate projected cash for each scenario
            # starting + (revenue - expenses) per month
            current_projected_cash = current_cash + (avg_revenue - avg_expenses) * month
            optimistic_projected_cash = current_cash + (optimistic_revenue - avg_expenses) * month
            pessimistic_projected_cash = current_cash + (avg_revenue - pessimistic_expenses) * month

            # Calculate remaining runway months
            current_runway_remaining = max(0, current_runway_months - month) if current_runway_months != float('inf') else float('inf')
            optimistic_runway_remaining = max(0, optimistic_runway_months - month) if optimistic_runway_months != float('inf') else float('inf')
            pessimistic_runway_remaining = max(0, pessimistic_runway_months - month) if pessimistic_runway_months != float('inf') else float('inf')

            runway_projections.append({
                "month": month,
                "current_cash": max(0, current_projected_cash),
                "optimistic_cash": max(0, optimistic_projected_cash),
                "pessimistic_cash": max(0, pessimistic_projected_cash),
                "current_runway_remaining": current_runway_remaining,
                "optimistic_runway_remaining": optimistic_runway_remaining,
                "pessimistic_runway_remaining": pessimistic_runway_remaining
            })

            # Stop projection when all scenarios reach zero cash
            if (current_projected_cash <= 0 and optimistic_projected_cash <= 0 and pessimistic_projected_cash <= 0):
                break

        return {
            "data": runway_projections,
            "summary": {
                "current_cash": current_cash,
                "avg_monthly_revenue": avg_revenue,
                "avg_monthly_expenses": avg_expenses,
                "current_net_flow": current_net_flow,
                "scenarios": {
                    "current": {
                        "runway_months": None if current_runway_months == float('inf') else current_runway_months,
                        "net_flow": current_net_flow,
                        "description": "Current trajectory"
                    },
                    "optimistic": {
                        "runway_months": None if optimistic_runway_months == float('inf') else optimistic_runway_months,
                        "net_flow": optimistic_net_flow,
                        "description": "Revenue +30%"
                    },
                    "pessimistic": {
                        "runway_months": None if pessimistic_runway_months == float('inf') else pessimistic_runway_months,
                        "net_flow": pessimistic_net_flow,
                        "description": "Expenses +20%"
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("API_ERROR", f"Error in /api/runway: {str(e)}", {"endpoint": "/api/runway"})
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, reload=True)