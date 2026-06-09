"use client";

import { useEffect } from "react";

export default function PresenceTracker() {
  useEffect(() => {
    const sendHeartbeat = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        await fetch(`${API_URL}/api/v1/presence/heartbeat`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (err) {
        console.error("Failed to send presence heartbeat:", err);
      }
    };

    // Send immediately on mount
    sendHeartbeat();

    // Send every 30 seconds
    const interval = setInterval(sendHeartbeat, 30000);

    // Visibility change listener to send heartbeat when user returns to tab
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        sendHeartbeat();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  return null;
}
