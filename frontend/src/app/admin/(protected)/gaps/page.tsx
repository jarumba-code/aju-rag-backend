"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { adminGaps, adminUpdateGap, GapRecord } from "@/lib/adminApi";

export default function GapsPage() {
  const [gaps, setGaps] = useState<GapRecord[]>([]);
  const [totalGaps, setTotalGaps] = useState(0);
  const [groupedByReason, setGroupedByReason] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadGaps = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminGaps({ limit: 30 });
      setGaps(data.recent_gaps);
      setTotalGaps(data.total_gaps);
      setGroupedByReason(data.grouped_by_reason);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load gaps.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGaps();
  }, []);

  const handleToggleResolved = async (gap: GapRecord) => {
    setUpdatingId(gap.id);
    try {
      const updated = await adminUpdateGap(gap.id, { resolved: !gap.resolved });
      setGaps((prev) =>
        prev.map((g) =>
          g.id === updated.id ? { ...g, resolved: updated.resolved, resolution_note: updated.resolution_note } : g
        )
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update gap.");
    } finally {
      setUpdatingId(null);
    }
  };

  const unresolved = gaps.filter((g) => !g.resolved).length;
  const resolved = gaps.filter((g) => g.resolved).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy aju-serif">Gaps &amp; Improvements</h1>
        <p className="text-sm text-slate-600 mt-1">Identify and address knowledge gaps detected by the RAG engine</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Total Gaps</h3>
            <AlertTriangle className="text-gold-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{totalGaps}</p>
          <p className="text-xs text-slate-500 mt-2">All-time unanswered queries</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Unresolved</h3>
            <Clock className="text-red-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{unresolved}</p>
          <p className="text-xs text-slate-500 mt-2">Needing attention</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Resolved</h3>
            <CheckCircle className="text-green-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{resolved}</p>
          <p className="text-xs text-slate-500 mt-2">Marked as addressed</p>
        </div>
      </div>

      {Object.keys(groupedByReason).length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Gaps by Reason</h2>
          <div className="flex flex-wrap gap-3">
            {Object.entries(groupedByReason).map(([reason, count]) => (
              <span
                key={reason}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700"
              >
                <span className="capitalize">{reason.replace(/_/g, " ")}</span>
                <span className="bg-slate-300 text-slate-800 rounded-full px-1.5">{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-navy mb-4">Recent Gaps</h2>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-gold-400 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-center">
            <p className="text-red-700 text-sm">{error}</p>
            <button
              onClick={loadGaps}
              className="mt-2 px-4 py-2 bg-gold-600 text-white rounded-lg text-sm hover:bg-gold-700"
            >
              Retry
            </button>
          </div>
        ) : gaps.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No knowledge gaps detected yet.</p>
        ) : (
          <div className="space-y-3">
            {gaps.map((gap) => (
              <div
                key={gap.id}
                className={`flex items-start gap-4 p-4 border rounded-lg transition-colors ${
                  gap.resolved ? "border-green-200 bg-green-50" : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {gap.resolved ? (
                    <CheckCircle className="text-green-500" size={20} />
                  ) : (
                    <AlertTriangle className="text-red-500" size={20} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{gap.query_text}</p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500 flex-wrap">
                    <span className="capitalize">{gap.reason?.replace(/_/g, " ")}</span>
                    {gap.confidence_score !== null && (
                      <span>Confidence: {gap.confidence_score.toFixed(3)}</span>
                    )}
                    {gap.created_at && (
                      <span>{new Date(gap.created_at).toLocaleDateString("en-NG")}</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleToggleResolved(gap)}
                  disabled={updatingId === gap.id}
                  className={`flex-shrink-0 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    gap.resolved
                      ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
                      : "bg-green-100 text-green-700 hover:bg-green-200"
                  } disabled:opacity-50`}
                >
                  {updatingId === gap.id ? "…" : gap.resolved ? "Reopen" : "Resolve"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
