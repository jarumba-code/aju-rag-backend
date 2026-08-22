"use client";

import { useState, useEffect } from "react";
import { ScrollText, Filter } from "lucide-react";
import { adminAuditLog, AuditLogRecord } from "@/lib/adminApi";

export default function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLogRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState("all");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const loadLogs = async (pageIndex: number, action: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminAuditLog({
        limit: PAGE_SIZE,
        offset: pageIndex * PAGE_SIZE,
        action: action !== "all" ? action : undefined,
      });
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs(0, filterAction);
    setPage(0);
  }, [filterAction]);

  const handlePageNext = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadLogs(nextPage, filterAction);
  };

  const handlePagePrev = () => {
    const prevPage = page - 1;
    setPage(prevPage);
    loadLogs(prevPage, filterAction);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Audit Log</h1>
          <p className="text-sm text-slate-600 mt-1">Track all administrative actions and system events</p>
        </div>
        <span className="text-sm text-slate-500">{total} total entries</span>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={20} className="text-slate-400" />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gold-500 text-sm"
          >
            <option value="all">All Actions</option>
            <option value="login">Login</option>
            <option value="logout">Logout</option>
            <option value="document_upload">Document Upload</option>
            <option value="document_delete">Document Delete</option>
            <option value="password_change">Password Change</option>
          </select>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-gold-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-center">
            <p className="text-red-700 text-sm">{error}</p>
            <button
              onClick={() => loadLogs(page, filterAction)}
              className="mt-2 px-4 py-2 bg-gold-600 text-white rounded-lg text-sm hover:bg-gold-700"
            >
              Retry
            </button>
          </div>
        ) : logs.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No audit log entries found.</p>
        ) : (
          <div className="space-y-2">
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-4 p-4 border border-slate-200 rounded-lg hover:bg-slate-50">
                <div className="p-2 bg-gold-100 rounded-lg flex-shrink-0">
                  <ScrollText className="text-gold-600" size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-slate-900 text-sm capitalize">{log.action.replace(/_/g, " ")}</h3>
                      {log.details && (
                        <p className="text-xs text-slate-600 mt-0.5 truncate max-w-md">{log.details}</p>
                      )}
                    </div>
                    <span className="text-xs text-slate-400 whitespace-nowrap flex-shrink-0">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString("en-NG") : "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 flex-wrap">
                    {log.user_role && <span>Role: <strong>{log.user_role}</strong></span>}
                    {log.resource_type && <span>Resource: {log.resource_type}{log.resource_id ? ` #${log.resource_id.slice(0, 8)}` : ""}</span>}
                    {log.ip_address && <span>IP: {log.ip_address}</span>}
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-medium ${
                      log.status === "success" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>{log.status}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && !error && total > PAGE_SIZE && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-200">
            <button
              onClick={handlePagePrev}
              disabled={page === 0}
              className="px-4 py-2 text-sm border border-slate-300 rounded-lg disabled:opacity-40 hover:bg-slate-50"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600">
              Page {page + 1} of {Math.ceil(total / PAGE_SIZE)}
            </span>
            <button
              onClick={handlePageNext}
              disabled={(page + 1) * PAGE_SIZE >= total}
              className="px-4 py-2 text-sm border border-slate-300 rounded-lg disabled:opacity-40 hover:bg-slate-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
