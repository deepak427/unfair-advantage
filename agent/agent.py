"""
Root agent — orchestrates rag_agent, graph_agent, and synthesis_agent.
Mirrors the agent_service/agent.py pattern exactly.
"""
import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from agent import prompt
from agent.sub_agents.rag_agent import create_rag_agent
from agent.sub_agents.graph_agent import create_graph_agent
from agent.sub_agents.synthesis_agent import create_synthesis_agent

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL_ROOT", "gemini-2.5-flash")
DESCRIPTION = (
    "Intelligent book assistant. Retrieves passages and graph relationships "
    "from ingested books, then synthesizes grounded, cited answers."
)

def create_root_agent(book_key: str) -> LlmAgent:
    rag_agent = create_rag_agent(book_key)
    graph_agent = create_graph_agent(book_key)
    synthesis_agent = create_synthesis_agent(book_key)

    if rag_agent and graph_agent and synthesis_agent:
        root_agent = LlmAgent(
            name=f"unfair_advantage_{book_key}",
            model=GEMINI_MODEL,
            description=DESCRIPTION,
            instruction=prompt.get_root_agent_prompt(book_key),
            tools=[
                AgentTool(rag_agent),
                AgentTool(graph_agent),
                AgentTool(synthesis_agent),
            ],
        )
        logger.info(f"Root agent created for book: {book_key}")
        return root_agent
    else:
        logger.error("Cannot create root agent: one or more sub-agents failed to initialize")
        return None

