"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { UserPlus, Loader2, Mail, User as UserIcon, RefreshCw, Key } from "lucide-react";
import Navbar from "@/components/Navbar";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();

  // Create User Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("doctor");
  const [presenceMap, setPresenceMap] = useState<Record<string, boolean>>({});

  const fetchPresence = async (userIds: string[]) => {
    if (userIds.length === 0) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/presence/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_ids: userIds }),
      });

      if (res.ok) {
        const data = await res.json();
        setPresenceMap(data);
      }
    } catch (err) {
      console.error("Failed to fetch presence status:", err);
    }
  };

  const fetchUsers = async () => {
    setError("");
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/admin/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 403) {
        throw new Error("Access denied. Admin role required.");
      }

      if (!res.ok) throw new Error("Failed to load users");
      const data = await res.json();
      setUsers(data);
      
      // Fetch presence status for all users immediately
      fetchPresence(data.map((u: User) => u.id));
    } catch (err: any) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Poll presence status of current user list every 15s
  useEffect(() => {
    if (users.length === 0) return;
    const interval = setInterval(() => {
      fetchPresence(users.map((u) => u.id));
    }, 15000);
    return () => clearInterval(interval);
  }, [users]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitLoading(true);

    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/admin/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
          role,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to create user");
      }

      setSuccess(`User ${email} created successfully!`);
      setEmail("");
      setPassword("");
      setFullName("");
      setRole("doctor");
      fetchUsers();
    } catch (err: any) {
      setError(err.message || "Failed to create user");
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-wide">Manage Users</h1>
            <p className="text-sm text-gray-400 mt-1">Register hospital staff and assign roles</p>
          </div>
          <button
            onClick={fetchUsers}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-all"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* User List Table */}
          <div className="glass-card rounded-2xl overflow-hidden lg:col-span-2">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-800/80 bg-gray-900/30 text-xs font-semibold tracking-wider text-gray-400 uppercase">
                    <th className="px-6 py-4">Full Name</th>
                    <th className="px-6 py-4">Email</th>
                    <th className="px-6 py-4">Role</th>
                    <th className="px-6 py-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/50 text-sm">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-6 py-10 text-center text-gray-500">
                        {loading ? "Loading users..." : "No users registered"}
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-800/10 transition-colors">
                        <td className="px-6 py-4 font-semibold text-gray-200">{u.full_name}</td>
                        <td className="px-6 py-4 text-gray-400">{u.email}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                            u.role === "admin"
                              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                              : u.role === "doctor"
                              ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                              : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-2">
                            {presenceMap[u.id] ? (
                              <>
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                <span className="text-xs font-semibold text-emerald-400">Online</span>
                              </>
                            ) : (
                              <>
                                <span className="h-2 w-2 rounded-full bg-gray-700"></span>
                                <span className="text-xs text-gray-500">Offline</span>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Create User Form */}
          <div className="glass-card p-6 rounded-2xl h-fit">
            <h2 className="text-xl font-bold mb-5 flex items-center space-x-2">
              <UserPlus className="h-5 w-5 text-sky-400" />
              <span>Create Staff User</span>
            </h2>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Full Name</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                    <UserIcon className="h-4 w-4" />
                  </span>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Dr. Gregory House"
                    className="block w-full pl-9 pr-4 py-2.5 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Email</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                    <Mail className="h-4 w-4" />
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="house@princeton.edu"
                    className="block w-full pl-9 pr-4 py-2.5 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Password</label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
                    <Key className="h-4 w-4" />
                  </span>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full pl-9 pr-4 py-2.5 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">System Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="block w-full px-4 py-2.5 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white outline-none transition-all text-sm"
                >
                  <option value="viewer">Viewer (Clinical staff)</option>
                  <option value="doctor">Doctor (Claim signer)</option>
                  <option value="admin">Administrator (System owner)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={submitLoading}
                className="w-full py-3 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 text-white font-semibold rounded-xl transition-all flex justify-center items-center space-x-2 text-sm mt-2"
              >
                {submitLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <span>Register Staff</span>
                )}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
