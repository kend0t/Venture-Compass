from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from typing import TypedDict, Annotated
from tools import tools
from IPython.display import Image, display
import os

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key = google_api_key
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
    # Simply invoke the model with tools and return the response
    response = model_with_tools.invoke(state["messages"])
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
        
        inputs = {"messages": [HumanMessage(content=query)]}
        print("Agent: ", end="", flush=True)

        # Stream all messages and collect the final response
        for msg, metadata in app.stream(inputs, config, stream_mode="messages"):
            # Print AI messages that have content and are not from humans
            if (isinstance(msg, AIMessage) and 
                msg.content and 
                not isinstance(msg, HumanMessage)):
                print(msg.content, end="", flush=True)
        
        print("\n")

queries = ["What is my current runway?","Can you show the computation breakdown?","What if I spent 50,000 this month?"]
user_agent_multiturn(queries)