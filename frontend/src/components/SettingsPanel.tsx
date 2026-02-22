"use client";

import { UserPreferences } from "@/types";
import { Settings, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface SettingsPanelProps {
  preferences: UserPreferences;
  onChange: (prefs: UserPreferences) => void;
}

export default function SettingsPanel({ preferences, onChange }: SettingsPanelProps) {
  const [open, setOpen] = useState(false);

  const update = (key: keyof UserPreferences, value: string | null) => {
    onChange({ ...preferences, [key]: value });
  };

  return (
    <div className="border-b border-parchment-300 bg-white">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-6 py-2 flex items-center gap-2 text-xs text-ink-50
                   hover:bg-parchment-50 transition-colors uppercase tracking-wider font-medium"
      >
        <Settings size={14} />
        Settings
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div className="px-6 pb-4 pt-2 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl">
          <div>
            <label className="block text-[11px] font-medium text-ink-50 uppercase tracking-wider mb-1.5">
              한국어 성경
            </label>
            <select
              value={preferences.translation_kr}
              onChange={(e) => update("translation_kr", e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-parchment-300 bg-parchment-50
                         text-sm text-ink-300 font-sans focus:outline-none focus:ring-2 focus:ring-gold-200"
            >
              <option value="개역한글">개역한글 (KRV, 1961)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-50 uppercase tracking-wider mb-1.5">
              English Bible
            </label>
            <select
              value={preferences.translation_en}
              onChange={(e) => update("translation_en", e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-parchment-300 bg-parchment-50
                         text-sm text-ink-300 font-sans focus:outline-none focus:ring-2 focus:ring-gold-200"
            >
              <option value="ESV">English Standard Version (ESV)</option>
              <option value="KJV">King James Version (KJV)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-ink-50 uppercase tracking-wider mb-1.5">
              교단 / Denomination
            </label>
            <select
              value={preferences.denomination ?? ""}
              onChange={(e) => update("denomination", e.target.value || null)}
              className="w-full px-3 py-2 rounded-lg border border-parchment-300 bg-parchment-50
                         text-sm text-ink-300 font-sans focus:outline-none focus:ring-2 focus:ring-gold-200"
            >
              <option value="">None — Show all views</option>
              <option value="Presbyterian">Presbyterian / 장로교</option>
              <option value="Baptist">Baptist / 침례교</option>
              <option value="Methodist">Methodist / 감리교</option>
              <option value="Pentecostal">Pentecostal / 순복음</option>
              <option value="Non-denominational">Non-denom / 비교단</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
