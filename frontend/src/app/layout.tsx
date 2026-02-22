import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "성경 AI 도우미 — Bible AI Assistant",
  description: "Bilingual Bible AI pastoral assistant for the Korean Christian community",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen flex flex-col overflow-hidden">{children}</body>
    </html>
  );
}
