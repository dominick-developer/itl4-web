# ai_service.py — Anthropic Claude integration for IT Expert Academy
import os
import re
from datetime import datetime

try:
    import anthropic
except ImportError:
    anthropic = None


# Model configuration
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# Pricing per 1M tokens (approximate, USD)
PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
}


def get_client():
    """Get Anthropic client or None if API key missing."""
    if anthropic is None:
        return None
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return None
    return anthropic.Anthropic(api_key=key)


def is_available():
    """Check if AI service is configured."""
    return get_client() is not None


LANGUAGE_INSTRUCTION = {
    "sw": "Respond entirely in Kiswahili (Swahili). Use simple, clear language suitable for a beginner.",
    "en": "Respond in clear, simple English suitable for a beginner.",
}


MODE_PROMPTS = {
    "explain": (
        "You are a patient, encouraging tutor. Explain the concept clearly with a "
        "real-world analogy and a small example. Break the explanation into short, "
        "digestible paragraphs. End with one short question to check understanding."
    ),
    "guide": (
        "You are a patient tutor. Guide the student step-by-step toward the answer. "
        "Do NOT reveal the full solution immediately. Ask what they have tried so far. "
        "Provide one clear next step at a time, then wait for their response."
    ),
    "hint": (
        "You are a patient tutor. Provide ONE concise hint to nudge the student in "
        "the right direction. Do not give the complete answer. Keep it under 3 sentences."
    ),
    "debug": (
        "You are a patient tutor helping debug code. Explain what the error means in "
        "plain language, then guide the student to fix it themselves. Only show the "
        "fixed line if they have tried and are still stuck after 2+ exchanges."
    ),
    "review": (
        "You are a tutor reviewing a student's code. Point out: (1) what works well, "
        "(2) what could be improved, (3) any bugs or edge cases. Be encouraging and "
        "specific. Do not rewrite their code for them."
    ),
    "practice": (
        "You are a tutor generating practice questions. Create 2-3 short questions "
        "based on the current lesson. Mix easy and moderate difficulty. Do not "
        "provide answers until the student attempts them."
    ),
}


def build_system_prompt(mode, language, lesson_context):
    """Compose system prompt for the tutor."""
    parts = []

    parts.append(
        "You are the AI Tutor for IT Expert Academy — a tech learning platform in Tanzania. "
        "Your role is to help learners understand concepts, not to complete their work for them. "
        "Always be respectful, encouraging, and clear. Never request passwords, API keys, or "
        "personal information. Never claim you executed code unless the system confirms it. "
        "If unsure, say so honestly."
    )

    parts.append(MODE_PROMPTS.get(mode, MODE_PROMPTS["explain"]))

    lang = LANGUAGE_INSTRUCTION.get(language, LANGUAGE_INSTRUCTION["sw"])
    parts.append(lang)

    if lesson_context:
        lc = (
            f"Current lesson: {lesson_context.get('lesson_title', 'N/A')}\n"
            f"Course: {lesson_context.get('course_title', 'N/A')}\n"
        )
        if lesson_context.get("lesson_content"):
            content = lesson_context["lesson_content"]
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
            lc += f"Lesson content excerpt: {content[:1500]}\n"
        parts.append(lc)

    return "\n\n".join(parts)


def _extract_text(response):
    """Safely extract text from response.content, skipping ThinkingBlock."""
    if not response or not getattr(response, "content", None):
        return ""
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text" or hasattr(block, "text"):
            txt = getattr(block, "text", "")
            if txt and txt.strip():
                return txt
    # Fallback: if no TextBlock found, try first block's .text (older models)
    try:
        return response.content[0].text or ""
    except Exception:
        return ""


def chat(mode, language, lesson_context, history, user_message):
    """
    Send a message to Claude and get a response.

    Returns:
        dict: {"ok": True, "text": str, "tokens_input": int, "tokens_output": int, "cost_usd": float}
        or {"ok": False, "error": str}
    """
    client = get_client()
    if client is None:
        return {
            "ok": False,
            "error": "AI service haijasanidiwa. Wasiliana na msimamizi (ANTHROPIC_API_KEY haipo).",
        }

    if not user_message or len(user_message.strip()) < 2:
        return {"ok": False, "error": "Ujumbe ni mfupi sana."}

    if len(user_message) > 4000:
        return {"ok": False, "error": "Ujumbe ni mrefu sana (kiwango cha juu ni herufi 4000)."}

    system_prompt = build_system_prompt(mode, language, lesson_context)

    # Build message list from history (last 10 messages for context window)
    messages = []
    for h in history[-10:]:
        sender = h.get("sender_type", "user")
        content = h.get("content", "")
        if not content:
            continue
        messages.append({
            "role": "user" if sender == "user" else "assistant",
            "content": content,
        })
    messages.append({"role": "user", "content": user_message.strip()})

    # Ensure messages start with user
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    # Ensure alternating roles (merge consecutive)
    merged = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n\n" + m["content"]
        else:
            merged.append(m)
    messages = merged

    if not messages or messages[0]["role"] != "user":
        return {"ok": False, "error": "Ujumbe wa kwanza unapaswa kuwa wa mtumiaji."}

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        text = _extract_text(response)
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        pricing = PRICING.get(MODEL, {"input": 1.0, "output": 5.0})
        cost = (tokens_in * pricing["input"] / 1_000_000) + (tokens_out * pricing["output"] / 1_000_000)

        if not text:
            return {"ok": False, "error": "AI ilirudisha jibu tupu. Jaribu tena."}

        return {
            "ok": True,
            "text": text,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cost_usd": round(cost, 6),
        }
    except Exception as e:
        err = str(e)
        if "rate_limit" in err.lower() or "429" in err:
            return {"ok": False, "error": "Kiwango cha maombi kimezidi. Subiri sekunde 30 kisha ujaribu tena."}
        if "authentication" in err.lower() or "401" in err:
            return {"ok": False, "error": "Hitilafu ya uthibitisho wa AI service. Wasiliana na msimamizi."}
        if "not_found" in err.lower() or "404" in err:
            return {"ok": False, "error": f"Model haipatikani ({MODEL}). Angalia ANTHROPIC_MODEL env var."}
        return {"ok": False, "error": f"Hitilafu ya AI: {err[:200]}"}