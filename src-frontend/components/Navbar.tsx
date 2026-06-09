"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, LogOut } from "lucide-react";

export default function Navbar() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const router = useRouter();

  useEffect(() => {
    setEmail(localStorage.getItem("email") || "");
    setRole(localStorage.getItem("role") || "");
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    router.push("/login");
  };

  return (
    <nav className="flex justify-between items-center px-8 py-4 border-b border-[var(--border)] bg-[#0d1321]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center space-x-6">
        <Link href="/dashboard" className="flex items-center space-x-2">
          <Activity className="h-6 w-6 text-sky-400" />
          <span className="font-bold text-lg tracking-wide bg-gradient-to-r from-sky-400 to-teal-400 bg-clip-text text-transparent">
            PulseAI Portal
          </span>
        </Link>
        <div className="hidden md:flex space-x-4 text-sm font-medium text-gray-300">
          <Link href="/dashboard" className="hover:text-white transition-all">Dashboard</Link>
          <Link href="/workflow/new" className="hover:text-white transition-all">New Case</Link>
          {role === "admin" && (
            <>
              <Link href="/admin/users" className="hover:text-white transition-all">Users</Link>
              <Link href="/admin/audit" className="hover:text-white transition-all">Audit Logs</Link>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right hidden sm:block">
          <p className="text-xs text-gray-500 capitalize">{role}</p>
          <p className="text-sm font-medium text-gray-300">{email}</p>
        </div>
        <button
          onClick={handleLogout}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-white transition-all"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </nav>
  );
}
