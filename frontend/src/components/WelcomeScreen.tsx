"use client";

import { BookOpen } from "lucide-react";

interface WelcomeScreenProps {
  onAsk: (question: string) => void;
}

const SUGGESTIONS = [
  { text: "오늘 QT 추천해주세요", label: "오늘 QT 추천" },
  { text: "What does the Bible say about anxiety?", label: "Bible & Anxiety" },
  { text: "로마서 8:28의 의미를 설명해주세요", label: "로마서 8:28 해설" },
  { text: "How should I pray according to Scripture?", label: "How to Pray" },
  { text: "구원의 확신에 대해 성경은 뭐라고 하나요?", label: "구원의 확신" },
  { text: "Explain the Trinity in simple terms", label: "The Trinity" },
];

export default function WelcomeScreen({ onAsk }: WelcomeScreenProps) {
  return (
    <div className="flex-1 flex items-center justify-center px-4">
      <div className="text-center max-w-lg">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gold-50 flex items-center justify-center mb-5">
          <BookOpen size={32} className="text-gold-300" />
        </div>

        <h2 className="font-serif text-2xl font-bold text-ink-300 mb-2">
          환영합니다! Welcome!
        </h2>

        <p className="text-ink-100 text-[15px] leading-relaxed mb-8">
          성경에 관해 궁금한 것을 물어보세요. 한국어와 영어 모두 사용 가능합니다.
          <br />
          Ask me anything about the Bible. I respond in both Korean and English.
        </p>

        <div className="flex flex-wrap gap-2 justify-center">
          {SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => onAsk(s.text)}
              className="px-4 py-2 rounded-full border border-parchment-300 bg-white
                         text-sm text-ink-100 hover:border-gold-200 hover:text-gold-300
                         hover:bg-gold-50 transition-all duration-200"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
