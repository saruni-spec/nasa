from typing import Dict, List, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler


from .tools import all_tools

from dataclasses import dataclass, field
from dotenv import load_dotenv


load_dotenv()


@dataclass
class AgentState:
    messages: List[Any] = field(default_factory=list)
    whatsapp_number: str = ""


def should_continue(state: AgentState) -> str:
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return "end"
    return "continue"


class NasaAgent:
    """
    AI Health Companion.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(all_tools)
        self.agent_graph = self._build_agentic_graph()
        self.langfuse = CallbackHandler()

    def _build_agentic_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)
        graph.add_node("call_model", self.call_model)
        graph.add_node("execute_tools", self.execute_tools)
        graph.set_entry_point("call_model")
        graph.add_conditional_edges(
            "call_model", should_continue, {"continue": "execute_tools", "end": END}
        )
        graph.add_edge("execute_tools", "call_model")
        return graph.compile()

    def call_model(self, state: AgentState) -> dict:
        print("🤖 Calling model...")
        response = self.llm_with_tools.invoke(state.messages)
        return {"messages": state.messages + [response]}

    def execute_tools(self, state: AgentState) -> dict:
        """
        Executes any tool calls made by the AI, processes the results,
        and returns them to be added to the state.
        """
        ai_message = state.messages[-1]
        tool_calls = ai_message.tool_calls
        if not tool_calls:
            raise ValueError("execute_tools was called without any tool_calls")

        tool_messages = []
        for tool_call in tool_calls:
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"🔧 Executing tool: {tool_name} with args: {tool_args}")

                tool_to_call = next((t for t in all_tools if t.name == tool_name), None)
                if not tool_to_call:
                    raise ValueError(f"Tool '{tool_name}' not found.")

                result = tool_to_call.invoke(tool_args)
                tool_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )
                print(f"✅ Tool '{tool_name}' executed successfully.")
            except Exception as e:
                print(f"❌ Error executing tool {tool_call['name']}: {e}")
                tool_messages.append(
                    ToolMessage(
                        content=f"Error: {str(e)}", tool_call_id=tool_call["id"]
                    )
                )

        return {"messages": state.messages + tool_messages}

    def _build_master_system_prompt(self) -> str:
        prompt_parts = [
            """
            ## Core Identity & Rules
            You are Titan, an AI assistant specialized in NASA bioscience research.
            You help researchers, mission planners, and scientists explore 608 NASA 
            bioscience publications to understand research progress, identify gaps,
            and provide actionable insights.
            
            ## Available Capabilities
            You have access to tools that can:
            - Search publications by keywords or full-text
            - Retrieve detailed article information
            - Analyze research trends and patterns
            - Identify knowledge gaps and understudied areas
            - Generate strategic insights for mission planning
            - Find related articles and research clusters
            
            ## Guidelines
            - Always use tools to answer questions with data
            - Be specific and cite PMCIDs when referencing articles
            - Identify knowledge gaps when discussing research areas
            - Provide actionable recommendations for mission planners
            - Be concise but comprehensive in your responses
            """
        ]
        return "\n".join(prompt_parts)

    def process_message_sync(self, user, message: str) -> Dict[str, Any]:
        try:

            master_prompt = self._build_master_system_prompt()
            system_prompts = [SystemMessage(content=master_prompt)]

            chat_history = []

            final_user_message = HumanMessage(content=message)
            final_message_list = system_prompts + chat_history + [final_user_message]

            initial_state = {"messages": final_message_list}
            final_state = self.agent_graph.invoke(
                initial_state, config={"callbacks": [self.langfuse]}
            )

            final_response = final_state["messages"][-1].content
            return {"response": final_response, "status": "success"}

        except Exception as e:
            print(f"Agent Error: {e}")
            return {"response": "A technical issue occurred.", "status": "error"}
