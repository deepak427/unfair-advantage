"""
Root agent — orchestrates rag_agent, graph_agent, and synthesis_agent.
Mirrors the agent_service/agent.py pattern exactly.
"""
import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from agent import prompt
from agent.sub_agents.rag_agent.rag_agent import rag_agent
from agent.sub_agents.graph_agent.graph_agent import graph_agent
from agent.sub_agents.synthesis_agent.synthesis_agent import synthesis_agent

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL_ROOT", "gemini-2.5-flash")
DESCRIPTION = (
    "Intelligent book assistant. Retrieves passages and graph relationships "
    "from ingested books, then synthesizes grounded, cited answers."
)

root_agent = None

if rag_agent and graph_agent and synthesis_agent:
    root_agent = LlmAgent(
        name="unfair_advantage",
        model=GEMINI_MODEL,
        description=DESCRIPTION,
        instruction=prompt.ROOT_AGENT_PROMPT,
        tools=[
            AgentTool(rag_agent),
            AgentTool(graph_agent),
            AgentTool(synthesis_agent),
        ],
    )
if root_agent:
    logger.info("Root agent 'unfair_advantage' created")
else:
    logger.error("Cannot create root agent: one or more sub-agents failed to initialize")

