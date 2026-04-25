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

synthesis_agent = None
try:
    synthesis_agent = LlmAgent(
        model=GEMINI_MODEL,
        name="synthesis_agent",
        description=DESCRIPTION,
        instruction=prompt.SYNTHESIS_AGENT_PROMPT,
        output_key="final_answer",
        # No tools — this agent only reasons over what's passed to it
    )
    logger.info(f"synthesis_agent created using {GEMINI_MODEL}")
except Exception as e:
    logger.error(f"Could not create synthesis_agent: {e}")
