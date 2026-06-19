import "./globals.css";
import PresenceTracker from "@/components/PresenceTracker";
import FloatingChatButton from "@/components/FloatingChatButton";
import ChatPanel from "@/components/ChatPanel";

export const metadata = {
  title: "PulseAI — Clinical Prior Authorization Platform",
  description:
    "HIPAA & TT46-compliant AI platform for hospital prior authorization workflows. Automate PA submissions in seconds.",
  keywords: "prior authorization, HIPAA, medical AI, hospital management, LangGraph",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#060d1f" />
      </head>
      <body>
        <PresenceTracker />
        {children}
        <FloatingChatButton />
        <ChatPanel />
      </body>
    </html>
  );
}

