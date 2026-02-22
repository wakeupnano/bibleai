export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Source[];
  retrieval_mode?: "rag" | "conversational";
}

export interface Source {
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

export interface UserPreferences {
  translation_kr: string;
  translation_en: string;
  denomination: string | null;
}
