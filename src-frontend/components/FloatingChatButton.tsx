"use client";

import { MessageSquare } from "lucide-react";
import { usePathname } from "next/navigation";

export default function FloatingChatButton() {
  const pathname = usePathname();
  const handleToggle = () => {
    window.dispatchEvent(new CustomEvent("toggle-chat"));
  };

  if (pathname === "/" || pathname === "/login") return null;

  return (
    <button
      onClick={handleToggle}
      className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-14 h-14 bg-teal-500 hover:bg-teal-600 text-white rounded-full shadow-xl transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:ring-offset-2 focus:ring-offset-[#060d1f]"
      aria-label="Toggle Chat Assistant"
      id="floating-chat-button"
    >
      <MessageSquare className="h-6 w-6" />
    </button>
  );
}
