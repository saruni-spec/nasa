from typing import Dict, List, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler


from models.db import db_config
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

    def __init__(self, google_api_key: str):
        self.llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(all_tools)
        self.user_service = UserService()
        self.db_config = db_config
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
        """
        Constructs a single, comprehensive, and token-optimized system prompt
        based on the user's current state.
        """

        prompt_parts = [
            """
            ## Core Identity & Rules
           
            """
        ]

        return "\n".join(prompt_parts)

    def process_message_sync(
        self,
        user: User,
        message: str,
    ) -> Dict[str, Any]:

        session = self.db_config.get_sync_session()

        try:
            # --- 1. BUILD THE MASTER SYSTEM PROMPT ---
            master_prompt = self._build_master_system_prompt(user)
            system_prompts = [SystemMessage(content=master_prompt)]

            # --- 2. LOAD CHAT HISTORY ---
            chat_history = []
            recent_messages_db = self.user_service.get_recent_messages(
                db=session, user_id=user.id
            )

            for msg in recent_messages_db:
                if msg.direction == MessageDirection.INBOUND:
                    chat_history.append(HumanMessage(content=msg.text_content))
                elif msg.direction == MessageDirection.OUTBOUND:
                    chat_history.append(AIMessage(content=msg.text_content))

        except Exception as e:
            print(f" DB Error: {e}")
            return {"response": "Error accessing records.", "status": "error"}
        finally:
            session.close()

        # --- 3. PREPARE AND INVOKE THE AGENT ---
        human_message_content = [{"type": "text", "text": message}]

        final_user_message = HumanMessage(content=human_message_content)
        final_message_list = system_prompts + chat_history + [final_user_message]

        try:
            initial_state = {"messages": final_message_list}

            final_state = self.agent_graph.invoke(
                initial_state, config={"callbacks": [self.langfuse]}
            )

            final_response = final_state["messages"][-1].content
            return {"response": final_response, "status": "success"}
        except Exception as e:
            print(f"Agent Error: {e}")
            return {"response": "A technical issue occurred.", "status": "error"}
