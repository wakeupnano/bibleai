"use client";

import { Message } from "@/types";
import { BookOpen } from "lucide-react";

interface ChatMessageProps {
  message: Message;
}

/**
 * Light formatting for bot responses: bold markers and citation highlights.
 * We use whitespace-pre-wrap on the container so newlines render natively
 * without needing a <br> regex hack. This also handles bulleted lists
 * that Claude tends to produce.
 */
function formatContent(text: string): string {
  let html = text;
  // **bold** to <strong>
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="text-gold-300">$1</strong>');
  // [Bible, ...] and [성경, ...] citation highlights
  html = html.replace(
    /\[(Bible|성경),\s*([^\]]+)\]/g,
    '<span class="text-gold-300 font-medium">[$1, $2]</span>'
  );
  return html;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 message-enter ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gold-50 flex items-center justify-center flex-shrink-0 mt-1">
          <BookOpen size={16} className="text-gold-300" />
        </div>
      )}

      <div className="max-w-[75%] min-w-[60px]">
        {isUser ? (
          <div className="bg-gold-300 text-white px-4 py-3 rounded-2xl rounded-br-sm text-[15px] leading-relaxed">
            <p>{message.content}</p>
          </div>
        ) : (
          <div className="bg-parchment-100 text-ink-300 px-5 py-4 rounded-2xl rounded-bl-sm text-[15px] leading-[1.8] shadow-sm whitespace-pre-wrap">
            <span dangerouslySetInnerHTML={{ __html: formatContent(message.content) }} />

            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-parchment-300 flex flex-wrap gap-1.5">
                {message.sources.map((s, i) => (
                  <span
                    key={i}
                    className="text-[11px] bg-gold-50 text-gold-300 px-2 py-0.5 rounded font-medium"
                  >
                    {s.reference} ({s.translation})
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
