"use client";

import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, MessageSquare, AlertTriangle } from "lucide-react";
import { adminAnalyticsSummary, adminAnalyticsTrends, AnalyticsSummary, AnalyticsTrends } from "@/lib/adminApi";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [s, t] = await Promise.all([
          adminAnalyticsSummary(),
          adminAnalyticsTrends(7),
        ]);
        if (!cancelled) {
          setSummary(s);
          setTrends(t);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load analytics.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadData();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center">
        <p className="text-red-700 text-sm mb-3">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-gold-600 text-white rounded-lg text-sm hover:bg-gold-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy aju-serif">Analytics &amp; Reports</h1>
        <p className="text-sm text-slate-600 mt-1">Monitor portal performance and usage statistics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Total Documents</h3>
            <BarChart3 className="text-gold-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{summary?.total_documents ?? 0}</p>
          <p className="text-xs text-slate-500 mt-2">Indexed in knowledge base</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Total Queries</h3>
            <MessageSquare className="text-gold-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{(summary?.total_answered ?? 0).toLocaleString()}</p>
          <p className="text-xs text-slate-500 mt-2">Answered by RAG engine</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Avg Confidence</h3>
            <TrendingUp className="text-gold-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{(summary?.avg_confidence ?? 0).toFixed(2)}</p>
          <p className="text-xs text-slate-500 mt-2">Similarity score</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-slate-600">Knowledge Gaps</h3>
            <AlertTriangle className="text-gold-500" size={20} />
          </div>
          <p className="text-3xl font-bold text-navy">{summary?.total_unanswered ?? 0}</p>
          <p className="text-xs text-slate-500 mt-2">Unresolved gaps</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Query Volume (Last 7 Days)</h2>
          {trends && trends.query_volume.labels.length > 0 ? (
            <div className="flex items-end gap-2 h-32">
              {trends.query_volume.labels.map((label, i) => {
                const maxVal = Math.max(...trends.query_volume.data, 1);
                const pct = (trends.query_volume.data[i] / maxVal) * 100;
                return (
                  <div key={label} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs text-slate-500">{trends.query_volume.data[i]}</span>
                    <div
                      className="w-full bg-gold-500 rounded-t"
                      style={{ height: `${Math.max(pct, 4)}%` }}
                    />
                    <span className="text-xs text-slate-400">{label}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-slate-400 text-sm">No query data available for this period.</p>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">System Performance</h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-slate-600">Resolution Rate</span>
                <span className="text-sm font-semibold text-green-600">{summary?.resolution_rate.toFixed(1) ?? 0}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${summary?.resolution_rate ?? 0}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-slate-600">Avg Response Time</span>
                <span className="text-sm font-semibold text-blue-600">{summary?.avg_latency_ms ?? 0} ms</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{ width: `${Math.min((summary?.avg_latency_ms ?? 0) / 30, 100)}%` }}
                />
              </div>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs text-slate-500">Total chunks indexed: <strong className="text-navy">{(summary?.total_chunks ?? 0).toLocaleString()}</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
