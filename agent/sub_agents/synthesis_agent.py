"""Synthesis sub-agent — reasons over retrieved content and produces grounded answers."""
import logging
import os
from google.adk.agents import LlmAgent
from agent import prompt

logger = logging.getLogger(__name__)

# Uses the more powerful reasoning model
GEMINI_MODEL = os.getenv("GEMINI_MODEL_REASONING", "gemini-2.5-pro")
DESCRIPTION = (
    "Reasons over retrieved book passages and graph relationships to produce a "
    "grounded, cited answer. Always cite sources. Never hallucinate."
)

def create_synthesis_agent(book_key: str) -> LlmAgent:
    try:
        agent = LlmAgent(
            model=GEMINI_MODEL,
            name=f"synthesis_agent_{book_key}",
            description=DESCRIPTION,
            instruction=prompt.get_synthesis_agent_prompt(book_key),
            output_key="final_answer",
            # No tools — this agent only reasons over what's passed to it
        )
        logger.info(f"synthesis_agent created using {GEMINI_MODEL} for book: {book_key}")
        return agent
    except Exception as e:
        logger.error(f"Could not create synthesis_agent: {e}")
        return None
