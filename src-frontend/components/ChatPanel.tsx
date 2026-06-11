"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { X, Send, Loader2, Sparkles, FileText } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I am your PulseAI Assistant. You can ask me questions about cases, or details to start a new prior authorization workflow.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastUserMessage, setLastUserMessage] = useState("");
  const [showCreateWorkflow, setShowCreateWorkflow] = useState(false);

  const pathname = usePathname();
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Extract workflow_id from pathname
  const workflowId = useMemo(() => {
    if (!pathname) return undefined;
    const parts = pathname.split("/");
    const idx = parts.indexOf("workflow");
    if (idx !== -1 && parts[idx + 1] && parts[idx + 1] !== "new") {
      return parts[idx + 1];
    }
    return undefined;
  }, [pathname]);

  // Handle panel toggle event
  useEffect(() => {
    const handleToggle = () => setIsOpen((prev) => !prev);
    const handleOpen = () => setIsOpen(true);

    window.addEventListener("toggle-chat", handleToggle);
    window.addEventListener("open-chat", handleOpen);

    return () => {
      window.removeEventListener("toggle-chat", handleToggle);
      window.removeEventListener("open-chat", handleOpen);
    };
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLastUserMessage(userMessage);
    setShowCreateWorkflow(false);

    // Append user message
    const updatedMessages = [...messages, { role: "user" as const, content: userMessage }];
    setMessages(updatedMessages);
    setLoading(true);

    const token = localStorage.getItem("token");
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    try {
      // API expects history without the system message and formatting
      // Standard history format: list of objects with role and content
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify({
          message: userMessage,
          workflow_id: workflowId || null,
          history: historyPayload,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to get response from AI assistant");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);

      if (data.action === "offer_create_workflow") {
        setShowCreateWorkflow(true);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error connecting to the server. Please make sure you are logged in and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWorkflow = () => {
    // Save last user message containing clinical details to localStorage
    localStorage.setItem("pending_clinical_text", lastUserMessage);
    setShowCreateWorkflow(false);
    setIsOpen(false);
    router.push("/workflow/new");
  };

  return (
    <div
      className={`fixed top-0 right-0 h-full w-[400px] z-50 bg-[#060d1f] border-l border-gray-800 shadow-2xl transition-transform duration-300 transform flex flex-col ${
        isOpen ? "translate-x-0" : "translate-x-full"
      }`}
      id="chat-assistant-panel"
    >
      {/* Panel Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-[#0a142c]">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-pulse" />
          <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider">
            PulseAI Chat Assistant
          </h2>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-white transition-colors"
          aria-label="Close panel"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Active Workflow Badge */}
      {workflowId && (
        <div className="px-4 py-2 bg-teal-500/10 border-b border-teal-500/20 flex items-center space-x-2">
          <FileText className="h-4 w-4 text-teal-400 shrink-0" />
          <span className="text-xs font-semibold text-teal-400 truncate">
            Active Case ID: {workflowId}
          </span>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-teal-600 text-white rounded-br-none"
                  : "bg-gray-800 text-gray-200 rounded-bl-none"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-xs flex items-center space-x-2">
              <Loader2 className="h-4 w-4 animate-spin text-teal-400" />
              <span>Assistant is typing...</span>
            </div>
          </div>
        )}

        {/* Create PA Workflow Action Suggestion */}
        {showCreateWorkflow && (
          <div className="p-3 bg-teal-500/5 border border-teal-500/20 rounded-xl space-y-2 animate-fade-in">
            <div className="flex items-center space-x-2">
              <Sparkles className="h-4 w-4 text-teal-400 shrink-0" />
              <p className="text-xs font-medium text-teal-300">
                Clinical Need Detected
              </p>
            </div>
            <p className="text-[11px] text-gray-400">
              I can automatically populate a new prior authorization request with the clinical details from our chat.
            </p>
            <button
              onClick={handleCreateWorkflow}
              className="w-full py-2 bg-teal-500 hover:bg-teal-600 text-white font-bold rounded-lg text-xs transition-colors flex items-center justify-center space-x-1.5"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>Create PA Workflow</span>
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-4 border-t border-gray-800 bg-[#091124]">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question or start a case..."
            disabled={loading}
            className="flex-1 bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-teal-500 placeholder-gray-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2.5 bg-teal-500 hover:bg-teal-600 text-white rounded-xl transition-all duration-150 flex items-center justify-center shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
