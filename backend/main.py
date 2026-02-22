"""
Bible AI Pastoral Assistant — FastAPI Backend

Endpoints:
- POST /api/chat          — Main chat endpoint (RAG + LLM)
- GET  /api/health        — Health check
- POST /api/search        — Direct Bible search (for debugging/testing)
- POST /api/chapter       — Get a full chapter
"""

import os
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# App Lifespan — Initialize services on startup
# ------------------------------------------------------------------
rag_service = None
llm_service = None

# In-memory session store (replace with Redis in production)
sessions: dict[str, list[dict]] = {}

# Similarity threshold — below this, the query is likely conversational
# (e.g., "Hello", "Thank you", "What should I read for QT today?")
CONVERSATIONAL_THRESHOLD = 0.25


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG and LLM services on startup."""
    global rag_service, llm_service

    from rag_service import BibleRAGService
    from llm_service import BibleLLMService

    chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    print("Initializing services...")
    rag_service = BibleRAGService(chroma_dir=chroma_dir)
    llm_service = BibleLLMService()
    print("Services ready!")

    yield

    print("Shutting down...")


# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------
app = FastAPI(
    title="Bible AI Pastoral Assistant",
    description="성경 AI 목회 도우미 — Bilingual Bible chatbot with RAG",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Dev frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Request/Response Models
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    preferences: Optional[dict] = None
    # preferences shape:
    # {
    #   "denomination": "Presbyterian" | "Baptist" | ... | null,
    #   "translation_kr": "개역한글",
    #   "translation_en": "KJV" | "ESV",
    # }


class ChatResponse(BaseModel):
    response: str
    session_id: str
    language: str
    sources: list[dict]  # Retrieved verses used as context
    retrieval_mode: str   # "rag" | "conversational" — helps frontend know what happened
    model: str
    usage: dict


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    n_results: int = Field(default=5, ge=1, le=20)
    translation: Optional[str] = None


class ChapterRequest(BaseModel):
    book: str
    chapter: int = Field(..., ge=1)
    translation: str = "KJV"


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    verse_count = rag_service.collection.count() if rag_service else 0
    return {
        "status": "healthy",
        "rag_initialized": rag_service is not None,
        "llm_initialized": llm_service is not None,
        "verse_count": verse_count,
        "esv_enabled": bool(os.getenv("ESV_API_KEY")) if rag_service else False,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint with intelligent retrieval routing.

    Uses sync def (not async) because ChromaDB and sentence-transformers are
    blocking libraries. FastAPI runs sync endpoints in a thread pool automatically,
    preventing event loop blocking for concurrent users.

    Pipeline:
    1. Search Bible verses via RAG (single search, reused for build_context)
    2. Check similarity scores — if low, this is a conversational query
    3. If relevant verses found: expand context + optional ESV swap
    4. If conversational: let the system prompt handle it naturally
    5. Send to Claude with context + conversation history
    """
    if not rag_service or not llm_service:
        raise HTTPException(status_code=503, detail="Services not initialized")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = []

    # Determine translation filter and ESV preference
    translation_filter = None
    use_esv = False
    if request.preferences:
        detected_lang = llm_service.detect_language(request.message)
        if detected_lang == "ko" and request.preferences.get("translation_kr"):
            translation_filter = request.preferences["translation_kr"]
        elif detected_lang == "en" and request.preferences.get("translation_en"):
            en_pref = request.preferences["translation_en"]
            if en_pref == "ESV":
                # ESV: search using KJV vectors, then swap text via API
                translation_filter = "KJV"
                use_esv = True
            else:
                translation_filter = en_pref

    # Step 1: Single search (reused by build_context — no double search)
    initial_verses = rag_service.search(
        query=request.message,
        n_results=8,
        translation_filter=translation_filter,
    )

    # Step 2: Check max similarity to determine retrieval mode
    max_sim = max([v["similarity"] for v in initial_verses]) if initial_verses else 0
    retrieval_mode = "rag" if max_sim >= CONVERSATIONAL_THRESHOLD else "conversational"

    # Step 3: Build context based on retrieval mode
    if retrieval_mode == "conversational":
        # Low relevance — user is asking a conversational question, greeting,
        # or recommendation (e.g., "QT 추천해주세요", "Hello", "Thank you")
        rag_context = (
            "No direct Bible text matched this query via vector search. "
            "The user is likely asking a conversational question, greeting, "
            "or requesting a recommendation (e.g., QT/quiet time suggestion, "
            "prayer guidance, or general faith conversation). "
            "Respond naturally using your general biblical knowledge and the "
            "system prompt guidelines. If recommending passages, suggest specific "
            "books/chapters the user might benefit from reading."
        )
        context_verses = []
    else:
        # Good relevance — pass pre-fetched verses (no redundant search)
        rag_context, context_verses = rag_service.build_context(
            initial_verses=initial_verses,
            prefer_esv=use_esv,
            expand_top_n=2,
            context_window=2,
        )

    # Step 4: Call LLM
    result = llm_service.chat(
        query=request.message,
        rag_context=rag_context,
        conversation_history=sessions[session_id],
        user_preferences=request.preferences,
    )

    # Step 5: Update session history (store the raw user message, not the RAG-augmented one)
    sessions[session_id].append({"role": "user", "content": request.message})
    sessions[session_id].append({"role": "assistant", "content": result["response"]})

    # Trim session history to last 20 messages (10 exchanges)
    if len(sessions[session_id]) > 20:
        sessions[session_id] = sessions[session_id][-20:]

    # Use context_verses (filtered, relevant) not raw initial_verses for display
    display_sources = context_verses[:5] if retrieval_mode == "rag" else []

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        language=result["language"],
        sources=display_sources,
        retrieval_mode=retrieval_mode,
        model=result["model"],
        usage=result["usage"],
    )


@app.post("/api/search")
def search_verses(request: SearchRequest):
    """Direct Bible verse search — useful for debugging and testing."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not initialized")

    verses = rag_service.search(
        query=request.query,
        n_results=request.n_results,
        translation_filter=request.translation,
    )

    return {"query": request.query, "results": verses}


@app.post("/api/chapter")
def get_chapter(request: ChapterRequest):
    """Get all verses from a specific chapter — for QT reading."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="RAG service not initialized")

    verses = rag_service.get_chapter(
        book=request.book,
        chapter=request.chapter,
        translation=request.translation,
    )

    if not verses:
        raise HTTPException(status_code=404, detail="Chapter not found")

    return {
        "book": request.book,
        "chapter": request.chapter,
        "translation": request.translation,
        "verses": verses,
    }


@app.delete("/api/session/{session_id}")
def clear_session(session_id: str):
    """Clear a conversation session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "cleared", "session_id": session_id}
