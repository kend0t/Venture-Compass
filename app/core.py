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

# Enable debug logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

google_api_key = os.getenv("GOOGLE_API_KEY")

# Optimized LLM configuration for faster streaming
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0,
    google_api_key=google_api_key,
)

def create_system_prompt(startup_name: str):
    """Create system prompt with startup context and explicit tool usage instructions"""
    return SystemMessage(content=f"""You are a financial advisor for startups/MSMEs. You are currently analyzing data for: {startup_name}

CRITICAL INSTRUCTIONS:
- ALWAYS use the available tools to get actual financial data
- When asked about runway, cash flow, or financial metrics, you MUST call the appropriate tools
- Never provide generic responses without using tools first
- If a tool fails, explain what went wrong and ask for manual data

AVAILABLE TOOLS:
1. get_financial_summary(startup_name="{startup_name}") - Get complete financial overview
2. calculate_runway_analysis(startup_name="{startup_name}") - Calculate runway and burn rate  
3. test_startup_data(startup_name="{startup_name}") - Test if data exists for the startup

TOOL USAGE RULES:
- When user asks about runway → ALWAYS call calculate_runway_analysis("{startup_name}")
- When user asks about finances → ALWAYS call get_financial_summary("{startup_name}")
- If you're unsure if data exists → call test_startup_data("{startup_name}") first
- ALWAYS pass the startup_name parameter: "{startup_name}"

CORE RESPONSIBILITIES:
- Calculate financial metrics accurately using tools provided
- ALWAYS provide a detailed computation breakdown for each metric computed
- If applicable, suggest 2-3 actionable improvements after showing calculations
- ALWAYS phrase suggestions as "You may want to consider", "You may want to explore"
- Use available tools to demonstrate scenarios
- Each segment of the response must have title in all caps and bold (e.g. **COMPUTATION BREAKDOWN**)

RESPONSE PATTERN:
1. Use appropriate tool to get data
2. Direct answer with calculations and computation breakdowns  
3. Health assessment with clear status
4. If financial products are needed, provide specific recommendations
5. Make every section well-spaced

Remember: You MUST use tools for any financial analysis. Never give generic responses about runway or cash flow without calling the tools first.""")

def create_chatbot_app(startup_name: str):
    """Create a chatbot application instance with startup-specific context"""
    
    print(f"DEBUG: Creating chatbot app for startup: {startup_name}")
    
    # Create startup-specific system prompt
    system_prompt = create_system_prompt(startup_name)
    
    # Tool binding with debugging
    tool_node = ToolNode(tools)
    model_with_tools = llm.bind_tools(tools)
    
    print(f"DEBUG: Available tools: {[tool.name for tool in tools]}")

    def should_continue(state: MessagesState):
        """Route chatbot → tools if tool calls exist, otherwise end."""
        try:
            last_message = state["messages"][-1]
            print(f"DEBUG: Last message type: {type(last_message)}")
            
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                print(f"DEBUG: Tool calls found: {last_message.tool_calls}")
                return "tools"
            else:
                print("DEBUG: No tool calls found, ending")
                return END
        except Exception as e:
            print(f"DEBUG: Error in should_continue: {str(e)}")
            log_error(
                error_type="ROUTING_ERROR",
                error_message=f"Error in should_continue function: {str(e)}",
                context={"state": str(state)[:500], "startup_name": startup_name}
            )
            return END

    def call_model(state: MessagesState):
        """Call model with startup-specific system prompt prepended."""
        try:
            messages = state["messages"]
            print(f"DEBUG: Input messages count: {len(messages)}")
            
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [system_prompt] + messages
                print("DEBUG: Added system prompt to messages")

            print(f"DEBUG: Calling model with {len(messages)} messages")
            print(f"DEBUG: Last user message: {messages[-1].content if messages else 'No messages'}")
            
            response = model_with_tools.invoke(messages)
            
            print(f"DEBUG: Model response type: {type(response)}")
            print(f"DEBUG: Model response content preview: {response.content[:200] if response.content else 'No content'}...")
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"DEBUG: Model requested {len(response.tool_calls)} tool calls:")
                for i, tool_call in enumerate(response.tool_calls):
                    print(f"DEBUG: Tool call {i}: {tool_call}")
            else:
                print("DEBUG: Model did not request any tool calls")

            return {"messages": [response]}
            
        except Exception as e:
            print(f"DEBUG: Error in call_model: {str(e)}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            log_error(
                error_type="MODEL_CALL_ERROR",
                error_message=f"Error calling language model: {str(e)}",
                context={
                    "message_count": len(state.get("messages", [])),
                    "last_message_type": type(state["messages"][-1]).__name__ if state.get("messages") else "None",
                    "startup_name": startup_name
                }
            )
            error_response = AIMessage(content="I apologize, but I'm experiencing technical difficulties. Please try your request again.")
            return {"messages": [error_response]}

    def safe_tool_execution(state: MessagesState):
        """Wrapper for tool execution with error handling"""
        try:
            print("DEBUG: Executing tools...")
            last_message = state["messages"][-1]
            if hasattr(last_message, 'tool_calls'):
                for tool_call in last_message.tool_calls:
                    print(f"DEBUG: Executing tool: {tool_call.get('name', 'unknown')} with args: {tool_call.get('args', {})}")
            
            result = tool_node.invoke(state)
            print(f"DEBUG: Tool execution completed successfully")
            return result
            
        except Exception as e:
            print(f"DEBUG: Error executing tools: {str(e)}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            log_error(
                error_type="TOOL_EXECUTION_ERROR",
                error_message=f"Error executing tools: {str(e)}",
                context={
                    "tool_calls": str(state["messages"][-1].tool_calls) if state.get("messages") and hasattr(state["messages"][-1], 'tool_calls') else "No tool calls found",
                    "startup_name": startup_name
                }
            )
            # Return error message
            error_message = AIMessage(content=f"I encountered an error while accessing the financial data for {startup_name}. The error was: {str(e)}. Please verify the startup name is correct or contact support if the issue persists.")
            return {"messages": state["messages"] + [error_message]}

    # Define workflow graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("chatbot", call_model)
    workflow.add_node("tools", safe_tool_execution)

    workflow.add_edge(START, "chatbot")
    workflow.add_conditional_edges("chatbot", should_continue, ["tools", END])
    workflow.add_edge("tools", "chatbot")

    # Memory for multi-turn chats
    memory = MemorySaver()

    try:
        app = workflow.compile(checkpointer=memory)
        print(f"DEBUG: Successfully compiled chatbot app for {startup_name}")
        return app
    except Exception as e:
        print(f"DEBUG: Failed to compile workflow: {str(e)}")
        log_error(
            error_type="WORKFLOW_COMPILATION_ERROR",
            error_message=f"Failed to compile workflow: {str(e)}",
            context={"workflow_nodes": ["chatbot", "tools"], "startup_name": startup_name}
        )
        raise