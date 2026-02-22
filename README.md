# Bible AI Pastoral Assistant (성경 AI 목회 도우미)

## System Architecture

**[ Next.js Web UI ]** │
       ▼
**[ FastAPI Server ]** ── (Searches) ──▶ **[ Chroma Database ]** (Bible text)
       │
       ▼
**[ Claude API ]** (Drafts response based ONLY on search results)


### RAG Pipeline

1. User sends a message
2. **Hybrid search**: Exact reference detection (regex for both Korean and English book names) + vector similarity search (multilingual embeddings)
3. **Context expansion**: Top results are expanded with ±2 surrounding verses for narrative understanding
4. **Low-similarity routing**: If no relevant verses found (score < 0.25), the system switches to conversational mode instead of forcing irrelevant passages
5. Context + system prompt + conversation history sent to Claude API
6. Response returned with inline citations and source tags

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Backend | Python FastAPI |
| Vector DB | ChromaDB (persistent, local) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (50+ languages incl. Korean) |
| LLM | Anthropic Claude API |

## Features

- Bilingual chat (Korean/English) with automatic language detection
- Hybrid verse retrieval: exact reference lookup + semantic vector search
- Context expansion: surrounding verses included for narrative understanding
- Proper citations with translation abbreviations on every claim
- Anti-hallucination: "Closed Book" rule — refuses to invent verses
- Pastoral response structure for devotional questions, direct answers for factual ones
- Denominational neutrality on secondary issues (neutral default, specific tradition on request)
- Sensitive topic protocol with crisis resources (988, 1393)
- Conversation memory within sessions
- Translation selector (KRV, KJV)
- Denomination preference selector (Presbyterian, Baptist, Methodist, etc.)

## Project Structure

```
bible-chatbot/
├── .gitignore
├── README.md
│
├── backend/
│   ├── .env.example            # Environment variables template
│   ├── requirements.txt        # Python dependencies
│   ├── system_prompt.py        # Finalized LLM system prompt
│   ├── rag_service.py          # Hybrid search + context expansion
│   ├── llm_service.py          # Claude API wrapper + language detection
│   └── main.py                 # FastAPI app (all endpoints)
│
├── frontend/
│   ├── package.json            # Node dependencies
│   ├── next.config.js          # API proxy configuration
│   ├── tsconfig.json           # TypeScript config
│   ├── tailwind.config.ts      # Custom parchment/gold/ink theme
│   ├── postcss.config.js       # PostCSS for Tailwind
│   └── src/
│       ├── app/
│       │   ├── globals.css     # Tailwind directives + fonts + animations
│       │   ├── layout.tsx      # Root HTML layout
│       │   └── page.tsx        # Main chat page (state + orchestration)
│       ├── components/
│       │   ├── ChatMessage.tsx  # User/bot message bubbles + source tags
│       │   ├── ChatInput.tsx    # Auto-resizing textarea + send button
│       │   ├── SettingsPanel.tsx # Translation + denomination selectors
│       │   ├── TypingIndicator.tsx
│       │   └── WelcomeScreen.tsx # Landing state + suggested questions
│       ├── lib/
│       │   └── api.ts          # Typed API client (fetch wrapper)
│       └── types/
│           └── index.ts        # Shared TypeScript interfaces
│
└── scripts/
    ├── ingest_bible.py         # Downloads KJV/KRV + builds ChromaDB
    └── run_tests.py            # Automated prompt test suite (22 tests)
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Clone and configure environment

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Ingest Bible data

Because vector databases and raw data files are too large for source control, the `data/` and `backend/chroma_db/` folders are intentionally not included in this repository. 

**Before starting the backend, you must generate the local database:**

1. Ensure your Python virtual environment is activated.
2. Run the ingestion script from the root directory:
   ```bash
   python scripts/ingest_bible.py
If the Korean auto-download fails, the script prints instructions for finding and saving the KRV JSON file manually.

```bash
cd scripts
python ingest_bible.py
```

This will:
- Download KJV (English) from a public domain GitHub source
- Attempt to auto-download KRV (Korean) from known sources
- Parse all verses into a flat structure with bilingual metadata
- Generate multilingual embeddings (~5 min on first run)
- Write everything into a persistent ChromaDB collection (~62,000 verses)

Korean file (개역한글) json file downloaded from the source: https://sieon-dev.tistory.com/127

The ingestion script handles two KRV JSON formats:
- Flat dictionary with abbreviations: `{"창1:14": "하나님이...", "롬8:28": "..."}`
- List-of-books with chapters: `[{"name": "창세기", "chapters": [[...], ...]}, ...]`

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Verify: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at [http://localhost:3000](http://localhost:3000). API calls go directly to `localhost:8000` (CORS configured).

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Main chat — RAG retrieval + Claude response |
| `GET` | `/api/health` | Server status and verse count |
| `POST` | `/api/search` | Direct Bible verse search (debugging) |
| `POST` | `/api/chapter` | Get all verses from a specific chapter |
| `DELETE` | `/api/session/{id}` | Clear a conversation session |

## Testing

An automated test suite validates 22 prompt scenarios across 8 categories:

| Category | Tests | What it checks |
|---|---|---|
| Citation Accuracy | 1A-1D | Real verses, fake book rejection, no hallucination |
| Language Detection | 2A-2C | Korean/English auto-detect, mixed-language |
| Response Structure | 3A-3C | Pastoral vs factual vs conversational format |
| Denominational Neutrality | 4A-4C | Baptism, tongues, neutral default |
| Sensitive Topics | 5A-5C | Crisis resources, abuse, addiction redirects |
| Conversation Awareness | 6A-6C | Multi-turn context retention |
| Edge Cases | 7A-7D | Gibberish, off-topic, out-of-scope |
| Korean Tone | 8A-8B | 하십시오체 formality, gospel presentation |

```bash
cd scripts

# Full suite (22 tests, ~3-5 min)
python run_tests.py

# Single category
python run_tests.py --category 5

# Single test
python run_tests.py --test 1C

# Verbose output
python run_tests.py --verbose
```

Results print to terminal and save to `test_results.json`.

## Bible Translations

| Translation | Language | Status | License |
|---|---|---|---|
| KRV (개역한글, 1961) | Korean | Active | Public domain |
| KJV | English | Active | Public domain |

## Theological Framework

- **Core**: Historic Protestant orthodoxy (Nicene Creed, Apostles' Creed, Five Solas)
- **Baseline**: Reformed evangelical, affirming sovereignty of God in salvation
- **Secondary issues**: Denominational neutrality by default. Presents the range of faithful Protestant views. Only prioritizes a specific tradition when the user explicitly asks.
- **Source hierarchy**: Scripture (Tier 1) > Creeds/Confessions (Tier 2) > Theological resources (Tier 3, Phase 2)

## Roadmap

- [x] Phase 1: Bible-only RAG MVP with bilingual support
- [x] Phase 1.5: Hybrid search, context expansion, multilingual embeddings, automated testing
- [ ] Phase 2: Add Desiring God + theological source RAG
- [ ] Phase 3: User onboarding, QT recommendations, daily devotionals
- [ ] Phase 4: Beta testing with Korean churches
- [ ] Phase 5: Mobile app (React Native), additional translations (ESV API, NKRV)
