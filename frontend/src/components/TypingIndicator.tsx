"use client";

import { BookOpen } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="flex gap-3 message-enter">
      <div className="w-8 h-8 rounded-lg bg-gold-50 flex items-center justify-center flex-shrink-0 mt-1">
        <BookOpen size={16} className="text-gold-300" />
      </div>
      <div className="bg-parchment-100 px-5 py-4 rounded-2xl rounded-bl-sm shadow-sm">
        <div className="flex gap-1.5">
          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-ink-50" />
          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-ink-50" />
          <span className="typing-dot w-1.5 h-1.5 rounded-full bg-ink-50" />
        </div>
      </div>
    </div>
  );
}
