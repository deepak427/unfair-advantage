"""RAG search sub-agent — retrieves passages from Vertex AI RAG Engine."""
import logging
import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from agent.tools.rag_search import search_rag
from agent import prompt

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL_ROOT", "gemini-2.5-flash")
DESCRIPTION = (
    "Retrieves relevant passages from the book knowledge base using semantic search. "
    "Use this for finding specific information, explanations, or quotes from books."
)

rag_agent = None
try:
    rag_agent = LlmAgent(
        model=GEMINI_MODEL,
        name="rag_agent",
        description=DESCRIPTION,
        instruction=prompt.RAG_AGENT_PROMPT,
        output_key="rag_results",
        tools=[FunctionTool(search_rag)],
    )
    logger.info(f"rag_agent created using {GEMINI_MODEL}")
except Exception as e:
    logger.error(f"Could not create rag_agent: {e}")
