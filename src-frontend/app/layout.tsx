import "./globals.css";
import PresenceTracker from "@/components/PresenceTracker";

export const metadata = {
  title: "PulseAI Portal",
  description: "Hospital Prior Authorization AI Portal",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <style>{`
          body {
            font-family: 'Outfit', sans-serif;
          }
        `}</style>
      </head>
      <body className="antialiased bg-[#0b0f19] text-[#f3f4f6]">
        <PresenceTracker />
        {children}
      </body>
    </html>
  );
}
