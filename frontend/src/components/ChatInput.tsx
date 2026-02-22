"use client";

import { SendHorizonal } from "lucide-react";
import { useRef, KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const value = textareaRef.current?.value.trim();
    if (!value || disabled) return;
    onSend(value);
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  };

  return (
    <div className="border-t border-parchment-300 bg-white px-4 sm:px-6 py-4 shadow-[0_-2px_8px_rgba(44,37,32,0.04)]">
      <div className="max-w-3xl mx-auto flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          placeholder="성경에 관해 물어보세요... / Ask about the Bible..."
          rows={1}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          className="flex-1 resize-none rounded-xl border border-parchment-300 bg-parchment-50
                     px-4 py-3 text-[15px] text-ink-300 font-sans leading-normal
                     placeholder:text-ink-50
                     focus:outline-none focus:ring-2 focus:ring-gold-200 focus:border-gold-200
                     min-h-[48px] max-h-[120px] transition-colors"
        />
        <button
          onClick={handleSend}
          disabled={disabled}
          className="w-12 h-12 flex-shrink-0 rounded-xl bg-gold-300 text-white flex items-center
                     justify-center hover:bg-gold-400 disabled:bg-ink-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          <SendHorizonal size={20} />
        </button>
      </div>
    </div>
  );
}
