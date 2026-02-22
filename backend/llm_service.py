"""
LLM Service — Manages Claude API interactions for Bible AI Assistant

Handles:
- System prompt injection
- RAG context integration
- Conversation history management
- Language detection
"""

import os
from typing import Optional
from anthropic import Anthropic
from langdetect import detect, LangDetectException
from system_prompt import SYSTEM_PROMPT


class BibleLLMService:
    """Manages LLM interactions with Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def detect_language(self, text: str) -> str:
        """Detect if input is Korean or English."""
        try:
            lang = detect(text)
            return "ko" if lang == "ko" else "en"
        except LangDetectException:
            return "en"  # Default to English

    def build_user_message(self, query: str, rag_context: str, language: str) -> str:
        """Build the user message with RAG context prepended."""
        lang_instruction = (
            "사용자가 한국어로 질문했습니다. 한국어로 답변해 주세요. 성경 구절은 개역한글 번역을 우선 인용하세요."
            if language == "ko"
            else "The user asked in English. Please respond in English. Cite Bible verses using KJV translation."
        )

        return f"""
{rag_context}

---
Language Instruction: {lang_instruction}
---

User Question: {query}
"""

    def chat(
        self,
        query: str,
        rag_context: str,
        conversation_history: list[dict] = None,
        user_preferences: dict = None,
    ) -> dict:
        """
        Send a message to Claude with RAG context and conversation history.

        Args:
            query: User's current message
            rag_context: Retrieved Bible passages formatted as context
            conversation_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]
            user_preferences: Dict with keys like "translation_kr", "translation_en", "denomination"

        Returns:
            Dict with "response" (text), "language" (detected), "model" (used)
        """
        # Detect language
        language = self.detect_language(query)

        # Build messages array
        messages = []

        # Add conversation history (last 10 exchanges max to manage context window)
        if conversation_history:
            recent_history = conversation_history[-20:]  # Last 10 exchanges (20 messages)
            messages.extend(recent_history)

        # Add current user message with RAG context
        user_message = self.build_user_message(query, rag_context, language)
        messages.append({"role": "user", "content": user_message})

        # Build dynamic system prompt with user preferences
        system = SYSTEM_PROMPT
        if user_preferences:
            pref_lines = ["\n\n## User Preferences (for this session):"]
            if user_preferences.get("denomination"):
                pref_lines.append(
                    f"- Denomination: {user_preferences['denomination']}. "
                    f"Prioritize this tradition's view on secondary issues while noting alternatives."
                )
            if user_preferences.get("translation_kr"):
                pref_lines.append(f"- Korean Bible translation: {user_preferences['translation_kr']}")
            if user_preferences.get("translation_en"):
                pref_lines.append(f"- English Bible translation: {user_preferences['translation_en']}")
            system += "\n".join(pref_lines)

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=messages,
        )

        response_text = response.content[0].text

        return {
            "response": response_text,
            "language": language,
            "model": self.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }
