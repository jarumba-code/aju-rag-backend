"use client";

import { useState } from "react";
import AdminShell from "@/components/AdminShell";
import { ScrollText, Filter, Download } from "lucide-react";

interface AuditEntry {
  id: string;
  action: string;
  user: string;
  timestamp: string;
  details: string;
  ipAddress: string;
}

const auditLogs: AuditEntry[] = [
  { id: "1", action: "Login", user: "admin@aju.edu.ng", timestamp: "2025-01-15 14:32:15", details: "Successful login", ipAddress: "192.168.1.100" },
  { id: "2", action: "Document Upload", user: "admin@aju.edu.ng", timestamp: "2025-01-15 14:28:03", details: "Uploaded Academic Calendar 2024/2025", ipAddress: "192.168.1.100" },
  { id: "3", action: "Password Change", user: "support@aju.edu.ng", timestamp: "2025-01-15 10:15:42", details: "Changed password successfully", ipAddress: "192.168.1.105" },
  { id: "4", action: "Logout", user: "admin@aju.edu.ng", timestamp: "2025-01-14 18:45:21", details: "User logged out", ipAddress: "192.168.1.100" },
  { id: "5", action: "Document Delete", user: "content@aju.edu.ng", timestamp: "2025-01-14 16:30:55", details: "Deleted old policy document", ipAddress: "192.168.1.110" },
];

export default function AuditLogPage() {
  const [filterAction, setFilterAction] = useState("all");

  const filteredLogs = filterAction === "all"
    ? auditLogs
    : auditLogs.filter(log => log.action.toLowerCase().includes(filterAction.toLowerCase()));

  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-navy aju-serif">Audit Log</h1>
            <p className="text-sm text-slate-600 mt-1">Track all administrative actions and system events</p>
          </div>
          <button className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50">
            <Download size={18} />
            Export Log
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center gap-2">
              <Filter size={20} className="text-slate-400" />
              <select
                value={filterAction}
                onChange={(e) => setFilterAction(e.target.value)}
                className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-500"
              >
                <option value="all">All Actions</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
                <option value="upload">Upload</option>
                <option value="delete">Delete</option>
              </select>
            </div>
          </div>

          <div className="space-y-3">
            {filteredLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-4 p-4 border border-slate-200 rounded-lg hover:bg-slate-50">
                <div className="p-2 bg-gold-100 rounded-lg">
                  <ScrollText className="text-gold-600" size={20} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-slate-900">{log.action}</h3>
                      <p className="text-sm text-slate-600 mt-1">{log.details}</p>
                    </div>
                    <span className="text-xs text-slate-500 whitespace-nowrap">{log.timestamp}</span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    <span>User: {log.user}</span>
                    <span>IP: {log.ipAddress}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
