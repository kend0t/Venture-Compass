from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools import tools
import os
import logging
from datetime import datetime
import traceback
from logger import log_error

load_dotenv()


google_api_key = os.getenv("GOOGLE_API_KEY")

# Optimized LLM configuration for faster streaming
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=google_api_key,
)

bank_products = [
    {
        "name": "Ka-Negosyo SME Loan",
        "description": "Supports the business in expanding product lines, purchasing new equipment, or meeting other capital expenditures.",
        "tenor": "1–5 years",
        "amount": "₱300,000 – ₱30,000,000",
        "collateral": "Optional to provide real estate mortgage, deposit, or investment"
    },
    {
        "name": "Ka-Negosyo Ready Loan",
        "description": "Ideal for businesses with seasonal funding needs.",
        "tenor": "3–6 months",
        "amount": "₱300,000 – ₱3,000,000",
        "collateral": "None"
    },
    {
        "name": "Ka-Negosyo Credit Line",
        "description": "Ideal for recurring business expenses such as inventory, employee salaries, utilities, equipment maintenance, and delivery costs.",
        "tenor": "1 year (renewable)",
        "amount": "₱1,000,000 – ₱30,000,000",
        "collateral": "Optional"
    },
    {
        "name": "Ka–Negosyo SME Loan for Property Acquisition",
        "description": "Ideal for acquisition or construction of property assets for your business.",
        "tenor": "1–10 years",
        "amount": "₱1,000,000 – ₱30,000,000",
        "collateral": "Real estate mortgage"
    }
]

def recommend_bank_products(context: str):
    """
    Recommend Ka-Negosyo products if context overlaps with product descriptions.
    """
    context = context.lower()
    recommendations = []

    for product in bank_products:
        if any(word in context for word in product["description"].lower().split()):
            recommendations.append(product)

    return recommendations

# System prompt for financial advisor chatbot
system_prompt = SystemMessage(content="""You are a financial advisor for startups/MSMEs.
CORE RESPONSIBILITIES:
- Calculate financial metrics accurately using tools provided.
- ALWAYS Provide a detailed computation breakdown for each metric computed.
- If applicable, suggest 2-3 actionable improvements after showing calculations.
- ALWAYS phrase suggestions as "You may want to consider", "You may want to explore", or any other similar phrases. Never directly instruct the user to do something.
- Use available tools to demonstrate scenarios.
- Each segment of the response must have title in all caps and bold(e.g. COMPUTATION BREAKDOWN)

FINANCIAL PRODUCT RECOMMENDATIONS:
- If funding is needed, only recommend from the following products:
  1. Ka-Negosyo SME Loan – For expansion, new equipment, or capital expenditures (₱300k–30M, 1–5 yrs, collateral optional)
  2. Ka-Negosyo Ready Loan – For seasonal funding needs (₱300k–3M, 3–6 mos, no collateral)
  3. Ka-Negosyo Credit Line – For recurring expenses like salaries, utilities, inventory, delivery costs (₱1M–30M, 1 yr renewable, collateral optional)
  4. Ka-Negosyo SME Loan for Property Acquisition – For property acquisition or construction (₱1M–30M, 1–10 yrs, real estate collateral)
- Trigger a product recommendation when:
  * Runway is in a **risky position (6–12 months)** or **critical (<6 months)**
  * The user mentions needing funding, working capital, or raising capital
  * The user discusses property acquisition, seasonal needs, or recurring expenses
- Choose only one product to recommend
- Start with "Here are the recommended BPI products for your scenario:"
- Do not invent other products. Only use these names.
- Always explain WHY the chosen (only one) recommended product fit the scenario.

RESPONSE PATTERN:
1. Direct answer with calculations and computation breakdowns
2. Health assessment with clear status
3. If financial products are needed, provide specific recommendations
4. Offer to show recommendations, make sure they are well-spaced
5. Make every section well-spaced
6. DO NOT mention the tools you are using or you are trying to use
""")

# Tool binding
tool_node = ToolNode(tools)
model_with_tools = llm.bind_tools(tools)

def should_continue(state: MessagesState):
    """Route chatbot → tools if tool calls exist, otherwise end."""
    try:
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END
    except Exception as e:
        log_error(
            error_type="ROUTING_ERROR",
            error_message=f"Error in should_continue function: {str(e)}",
            context={"state": str(state)[:500]}  # Limit context size
        )
        return END

def call_model(state: MessagesState):
    """Call model with system prompt prepended (LLM handles recommendations)."""
    try:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [system_prompt] + messages

        response = model_with_tools.invoke(messages)

        return {"messages": [response]}
        
    except Exception as e:
        log_error(
            error_type="MODEL_CALL_ERROR",
            error_message=f"Error calling language model: {str(e)}",
            context={
                "message_count": len(state.get("messages", [])),
                "last_message_type": type(state["messages"][-1]).__name__ if state.get("messages") else "None"
            }
        )
        error_response = AIMessage(content="I apologize, but I'm experiencing technical difficulties. Please try your request again.")
        return {"messages": [error_response]}

# def call_model(state: MessagesState):
#     """Call model with system prompt prepended."""
#     try:
#         messages = state["messages"]
#         if not messages or not isinstance(messages[0], SystemMessage):
#             messages = [system_prompt] + messages

#         response = model_with_tools.invoke(messages)
#         #     # --- NEW: Check if recommendation is needed ---
#         user_query = messages[-1].content.lower()
#         agent_reply = response.content.lower()

#         # # Only trigger if funding/loan context is detected
#         # if any(word in user_query + agent_reply for word in 
#         #     ["funding", "fundraising", "loan", "credit", 
#         # "raise capital", "short runway", "working capital", 
#         # "cash flow", "property purchase", "seasonal", "runway"]):
            
#         #     recs = recommend_bank_products(user_query + agent_reply)
#         #     if recs:
#         #         product_text = "\n\n**BANK PRODUCT RECOMMENDATIONS:**"
#         #         for r in recs:
#         #             product_text += f"\n- **{r['name']}**: {r['description']} (₱{r['amount']}, Tenor: {r['tenor']}, Collateral: {r['collateral']})"
                
#         #         # Append to model's response
#         #         response.content += product_text

#         trigger_keywords = [
#     "funding", "fundraising", "loan", "credit", 
#     "raise capital", "short runway", "working capital", 
#     "cash flow", "property purchase", "seasonal", "runway"
# ]
#         if any(word in user_query + agent_reply for word in trigger_keywords):
#             recs = recommend_bank_products(user_query + agent_reply)
#             if recs:
#                 product_text = "\n\n**BANK PRODUCT RECOMMENDATIONS:**"
#                 for r in recs:
#                     product_text += (
#                         f"\n- **{r['name']}**: {r['description']} "
#                         f"(₱{r['amount']}, Tenor: {r['tenor']}, Collateral: {r['collateral']})"
#                     )
#                 response.content += product_text


#         return {"messages": [response]}
        
#     except Exception as e:
#         log_error(
#             error_type="MODEL_CALL_ERROR",
#             error_message=f"Error calling language model: {str(e)}",
#             context={
#                 "message_count": len(state.get("messages", [])),
#                 "last_message_type": type(state["messages"][-1]).__name__ if state.get("messages") else "None"
#             }
#         )
#         # Return error message instead of crashing
#         error_response = AIMessage(content="I apologize, but I'm experiencing technical difficulties. Please try your request again.")
#         return {"messages": [error_response]}

def safe_tool_execution(state: MessagesState):
    """Wrapper for tool execution with error handling"""
    try:
        return tool_node.invoke(state)
    except Exception as e:
        log_error(
            error_type="TOOL_EXECUTION_ERROR",
            error_message=f"Error executing tools: {str(e)}",
            context={
                "tool_calls": str(state["messages"][-1].tool_calls) if state.get("messages") and hasattr(state["messages"][-1], 'tool_calls') else "No tool calls found"
            }
        )
        # Return error message
        error_message = AIMessage(content="I encountered an error while performing the financial calculations. Please try rephrasing your question or contact support if the issue persists.")
        return {"messages": state["messages"] + [error_message]}

# Define workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", call_model)
workflow.add_node("tools", safe_tool_execution)  # Use safe wrapper

workflow.add_edge(START, "chatbot")
workflow.add_conditional_edges("chatbot", should_continue, ["tools", END])
workflow.add_edge("tools", "chatbot")

# Memory for multi-turn chats
memory = MemorySaver()

try:
    app = workflow.compile(checkpointer=memory)
except Exception as e:
    log_error(
        error_type="WORKFLOW_COMPILATION_ERROR",
        error_message=f"Failed to compile workflow: {str(e)}",
        context={"workflow_nodes": ["chatbot", "tools"]}
    )
    raise

# Default config (can be overridden by thread_id in main.py)
config = {"configurable": {"thread_id": "1"}}