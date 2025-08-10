from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools import tools
import os

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key = google_api_key,
)

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
                              """
                              )

tool_node = ToolNode(tools)
model_with_tools = llm.bind_tools(tools)

def should_continue(state: MessagesState):
    # Get the last message from the state
    last_message = state["messages"][-1]
    
    # Check if the last message includes tool calls
    if last_message.tool_calls:
        return "tools"
    
    # End the conversation if no tool calls are present
    return END

def call_model(state: MessagesState):
    messages = state['messages']
    if not messages or not isinstance(messages[0],SystemMessage):
        messages = [system_prompt] + messages
        
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

# Add nodes for chatbot and tools
workflow = StateGraph(MessagesState)
workflow.add_node("chatbot", call_model)
workflow.add_node("tools", tool_node)

# Define an edge connecting START to the chatbot
workflow.add_edge(START, "chatbot")

# Define conditional edges and route "tools" back to "chatbot"
workflow.add_conditional_edges("chatbot", should_continue, ["tools", END])
workflow.add_edge("tools", "chatbot")

# Set up memory and compile the workflow
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "1"}} 

def user_agent_multiturn(queries):  
    for query in queries:
        print(f"User: {query}")
        
        enhanced_query = query
        if any(keyword in query.lower() for keyword in ["runway", "burn", "cash", "expenses"]):
            enhanced_query += " Please also suggest specific actions I should consider."
        
        inputs = {"messages": [HumanMessage(content=enhanced_query)]}
        print("Agent: ", end="", flush=True)

        # Stream all messages and collect the final response
        for msg, metadata in app.stream(inputs, config, stream_mode="messages"):
            # Print AI messages that have content and are not from humans
            if (isinstance(msg, AIMessage) and 
                msg.content and 
                not isinstance(msg, HumanMessage)):
                print(msg.content, end="", flush=True)
        
        print("\n")

queries = ["What is my burn rate this month?","What is my current runway?","If I spend 50k next month, what should be my revenue to maintain my runway?"]
user_agent_multiturn(queries)