"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { BookOpen } from "lucide-react";
import { Message, UserPreferences } from "@/types";
import { sendMessage } from "@/lib/api";
import SettingsPanel from "@/components/SettingsPanel";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import TypingIndicator from "@/components/TypingIndicator";
import WelcomeScreen from "@/components/WelcomeScreen";

export default function Home() {
  // ------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [preferences, setPreferences] = useState<UserPreferences>({
    translation_kr: "개역한글",
    translation_en: "ESV",
    denomination: null,
  });
  const [error, setError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // ------------------------------------------------------------------
  // Auto-scroll on new messages
  // ------------------------------------------------------------------
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // ------------------------------------------------------------------
  // Send Message
  // ------------------------------------------------------------------
  const handleSend = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;
      setError(null);

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const response = await sendMessage({
          message: text.trim(),
          session_id: sessionId,
          preferences,
        });

        setSessionId(response.session_id);

        const botMsg: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.response,
          sources: response.sources,
          retrieval_mode: response.retrieval_mode,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, botMsg]);
      } catch (err) {
        const errorMessage =
          err instanceof Error && err.message.includes("Failed to fetch")
            ? "서버에 연결할 수 없습니다. 백엔드를 실행해주세요.\nCannot connect to server. Please start the backend."
            : `오류가 발생했습니다. 다시 시도해주세요.\n${err instanceof Error ? err.message : "Unknown error"}`;
        setError(errorMessage);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, sessionId, preferences]
  );

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  const hasMessages = messages.length > 0;

  return (
    <>
      {/* Header */}
      <header className="bg-white border-b border-parchment-300 px-4 sm:px-6 py-3 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gold-50 flex items-center justify-center">
            <BookOpen size={20} className="text-gold-300" />
          </div>
          <div>
            <h1 className="font-serif font-bold text-lg text-ink-300 leading-tight">
              성경 AI 도우미
            </h1>
            <p className="text-xs text-ink-50 font-light">
              Bible AI Pastoral Assistant
            </p>
          </div>
        </div>
      </header>

      {/* Settings */}
      <SettingsPanel preferences={preferences} onChange={setPreferences} />

      {/* Chat Area */}
      {!hasMessages ? (
        <WelcomeScreen onAsk={handleSend} />
      ) : (
        <div className="flex-1 overflow-y-auto chat-scroll px-4 sm:px-6 py-6">
          <div className="max-w-3xl mx-auto flex flex-col gap-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}

            {/* Error */}
            {error && (
              <div className="message-enter bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm whitespace-pre-line">
                {error}
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>
      )}

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </>
  );
}
