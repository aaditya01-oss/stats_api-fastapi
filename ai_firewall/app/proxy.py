"""
proxy.py — The core proxy logic.

Intercepts incoming LLM requests, scores the prompt,
logs the decision, and either forwards to the LLM or blocks.

This is the heart of the AI Firewall.
"""

import httpx
import os
from app.scorer import PromptScorer
from app.logger import log_request


# The actual LLM API endpoint we're proxying to
# In production this would be the real Anthropic/OpenAI endpoint
LLM_API_URL = os.getenv(
    "LLM_API_URL",
    "https://api.anthropic.com/v1/messages"
)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Single scorer instance — loaded once at startup
# Loading the NLP model is expensive, we don't want to do it per request
scorer = PromptScorer(threshold=0.7)


async def process_request(payload: dict) -> dict:
    """
    Core firewall logic — intercepts, scores, decides, forwards or blocks.

    Args:
        payload: the full request body intended for the LLM

    Returns:
        dict with either the LLM response or a block message
    """
    # Extract the prompt from the payload
    # Handles both simple {"prompt": "..."} and
    # Anthropic-style {"messages": [{"role": "user", "content": "..."}]}
    prompt = extract_prompt(payload)

    # Score the prompt
    analysis = scorer.score(prompt)

    # Log every request — safe and blocked alike
    log_request(analysis)

    # Decision
    if analysis["is_malicious"]:
        return {
            "blocked": True,
            "reason": "Prompt injection detected",
            "score": analysis["score"],
            "detection_method": analysis["detection_method"],
            "message": (
                "Your request was blocked by the AI Firewall. "
                "Prompt injection attempts are not permitted."
            )
        }

    # Safe — forward to the real LLM
    if LLM_API_KEY:
        return await forward_to_llm(payload)
    else:
        # No API key configured — return mock response for testing
        return {
            "blocked": False,
            "score": analysis["score"],
            "message": "Prompt passed firewall checks.",
            "mock_response": "LLM_API_KEY not configured — this is a mock response.",
        }


def extract_prompt(payload: dict) -> str:
    """
    Extracts the prompt text from various payload formats.
    Handles simple and Anthropic-style message formats.
    """
    # Simple format: {"prompt": "..."}
    if "prompt" in payload:
        return str(payload["prompt"])

    # Anthropic format: {"messages": [{"role": "user", "content": "..."}]}
    if "messages" in payload:
        messages = payload["messages"]
        user_messages = [
            m["content"] for m in messages
            if m.get("role") == "user"
        ]
        return " ".join(user_messages)

    return str(payload)


async def forward_to_llm(payload: dict) -> dict:
    """
    Forwards a safe prompt to the real LLM API.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            LLM_API_URL,
            json=payload,
            headers={
                "x-api-key": LLM_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=30.0,
        )
        return response.json()