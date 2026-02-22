import { UserPreferences } from "@/types";

const API_BASE = "http://localhost:8000/api";

interface ChatRequest {
  message: string;
  session_id: string | null;
  preferences: UserPreferences;
}

interface ChatResponse {
  response: string;
  session_id: string;
  language: string;
  sources: Source[];
  retrieval_mode: "rag" | "conversational";
  model: string;
  usage: { input_tokens: number; output_tokens: number };
}

interface Source {
  text: string;
  reference: string;
  reference_kr: string;
  translation: string;
  book: string;
  book_kr: string;
  chapter: number;
  verse: number;
  similarity?: number;
}

interface HealthResponse {
  status: string;
  rag_initialized: boolean;
  llm_initialized: boolean;
  verse_count: number;
  esv_enabled: boolean;
}

export async function sendMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Server error ${response.status}: ${detail}`);
  }

  return response.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error("Health check failed");
  return response.json();
}

export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/session/${sessionId}`, { method: "DELETE" });
}
