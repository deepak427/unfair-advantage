"""Graph search sub-agent — finds relationships in Neo4j via Graphiti."""
import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from agent.tools.graph_search import search_graph
from agent import prompt

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL_ROOT", "gemini-2.5-flash")
DESCRIPTION = (
    "Searches the knowledge graph for relationships and connections between concepts "
    "across books. Use this for 'how does X relate to Y?' type questions."
)

def create_graph_agent(book_key: str) -> LlmAgent:
    try:
        agent = LlmAgent(
            model=GEMINI_MODEL,
            name=f"graph_agent_{book_key}",
            description=DESCRIPTION,
            instruction=prompt.get_graph_agent_prompt(book_key),
            output_key="graph_results",
            tools=[FunctionTool(search_graph)],
        )
        logger.info(f"graph_agent created using {GEMINI_MODEL} for book: {book_key}")
        return agent
    except Exception as e:
        logger.error(f"Could not create graph_agent: {e}")
        return None
