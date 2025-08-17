from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools import tools
import os

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

# Optimized LLM configuration for faster streaming
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=google_api_key,
)

# System prompt for financial advisor chatbot
system_prompt = SystemMessage(content="""You are a financial advisor for startups/MSMEs.
CORE RESPONSIBILITIES:
- Calculate financial metrics accurately using tools provided.
- ALWAYS Provide a detailed computation breakdown for each metric computed.
- ALWAYS suggest 2-3 actionable improvements after showing calculations.
- ALWAYS phrase suggestions as "You may want to consider", "You may want to explore", or any other similar phrases. Never directly instruct the user to do something.
- Use available tools to demonstrate scenarios.

RESPONSE PATTERN:
1. Direct answer with calculations and computation breakdowns
2. Health assessment with clear status
3. Offer to show recommendations
4. Offer to show detailed scenarios
""")

# Tool binding
tool_node = ToolNode(tools)
model_with_tools = llm.bind_tools(tools)

def should_continue(state: MessagesState):
    """Route chatbot → tools if tool calls exist, otherwise end."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

def call_model(state: MessagesState):
    """Call model with system prompt prepended."""
    messages = state["messages"]
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_prompt] + messages

    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

# Define workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "chatbot")
workflow.add_conditional_edges("chatbot", should_continue, ["tools", END])
workflow.add_edge("tools", "chatbot")

# Memory for multi-turn chats
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# Default config (can be overridden by thread_id in main.py)
config = {"configurable": {"thread_id": "1"}}
