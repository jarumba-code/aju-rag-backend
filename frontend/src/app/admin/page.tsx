"use client";

import { useState, useEffect } from "react";
import AdminShell from "@/components/AdminShell";
import { LayoutDashboard, FileText, MessageSquare, Users, TrendingUp, AlertTriangle } from "lucide-react";

interface DashboardStats {
  totalDocuments: number;
  totalQueries: number;
  activeUsers: number;
  knowledgeGaps: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalQueries: 0,
    activeUsers: 0,
    knowledgeGaps: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setStats({
        totalDocuments: 156,
        totalQueries: 15420,
        activeUsers: 342,
        knowledgeGaps: 12,
      });
      setLoading(false);
    }, 800);
  }, []);

  if (loading) {
    return (
      <AdminShell>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-600">Loading dashboard...</p>
          </div>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Dashboard</h1>
          <p className="text-sm text-slate-600 mt-1">Welcome to the AJU Admin Portal</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Total Documents</h3>
              <FileText className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.totalDocuments}</p>
            <p className="text-xs text-green-600 mt-2">+12 this month</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Total Queries</h3>
              <MessageSquare className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.totalQueries.toLocaleString()}</p>
            <p className="text-xs text-green-600 mt-2">+15.3% from last month</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Active Users</h3>
              <Users className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.activeUsers}</p>
            <p className="text-xs text-green-600 mt-2">Currently online</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Knowledge Gaps</h3>
              <AlertTriangle className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.knowledgeGaps}</p>
            <p className="text-xs text-yellow-600 mt-2">5 require attention</p>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-navy mb-4">Recent Activity</h2>
            <div className="space-y-3">
              {[
                { action: "Document uploaded", user: "admin@aju.edu.ng", time: "2 minutes ago" },
                { action: "User login", user: "support@aju.edu.ng", time: "15 minutes ago" },
                { action: "Password changed", user: "admin@aju.edu.ng", time: "1 hour ago" },
                { action: "Question approved", user: "content@aju.edu.ng", time: "2 hours ago" },
              ].map((activity, idx) => (
                <div key={idx} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{activity.action}</p>
                    <p className="text-xs text-slate-500">{activity.user}</p>
                  </div>
                  <span className="text-xs text-slate-400">{activity.time}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-lg font-semibold text-navy mb-4">System Health</h2>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-600">API Response Time</span>
                  <span className="text-sm font-semibold text-green-600">Excellent</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: "95%" }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-600">Database Performance</span>
                  <span className="text-sm font-semibold text-green-600">Good</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full" style={{ width: "88%" }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-600">Storage Usage</span>
                  <span className="text-sm font-semibold text-yellow-600">Moderate</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div className="bg-yellow-500 h-2 rounded-full" style={{ width: "65%" }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}

  if (loading) {
    return (
      <AdminShell>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-600">Loading dashboard...</p>
          </div>
        </div>
      </AdminShell>
    );
  }

  if (error) {
    return (
      <AdminShell>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <p className="text-red-600 mb-2">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-gold-600 text-white rounded-lg hover:bg-gold-700"
            >
              Retry
            </button>
          </div>
        </div>
      </AdminShell>
    );
  }
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Recent Activity</h2>
          {recentActivity.length === 0 ? (
            <p className="text-sm text-slate-500">No recent activity.</p>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((log) => (
                <div key={log.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{log.action.replace(/_/g, " ")}</p>
                    <p className="text-xs text-slate-500">
                      {log.details || `${log.resource_type || "System"}${log.resource_id ? ` #${log.resource_id}` : ""}`}
                    </p>
                  </div>
                  <span className="text-xs text-slate-400">
                    {new Date(log.timestamp).toLocaleString("en-NG")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  );
}
"use client";

import { useState, useEffect } from "react";
import AdminShell from "@/components/AdminShell";
import { FileText, MessageSquare, AlertTriangle, Activity } from "lucide-react";
import { adminAnalyticsSummary, adminAuditLog, AnalyticsSummary, AuditLogRecord } from "@/lib/adminApi";

interface DashboardStats {
  totalDocuments: number;
  totalQueries: number;
  knowledgeGaps: number;
  resolutionRate: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalDocuments: 0,
    totalQueries: 0,
    knowledgeGaps: 0,
    resolutionRate: 0,
  });
  const [recentActivity, setRecentActivity] = useState<AuditLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [summary, auditData] = await Promise.all([
          adminAnalyticsSummary(),
          adminAuditLog({ limit: 4 }),
        ]);

        if (cancelled) return;

        setStats({
          totalDocuments: summary.total_documents,
          totalQueries: summary.total_answered,
          knowledgeGaps: summary.total_unanswered,
          resolutionRate: summary.resolution_rate,
        });

        setRecentActivity(auditData.logs.slice(0, 4));
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadData();
    return () => { cancelled = true; };
  }, []);
  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Dashboard</h1>
          <p className="text-sm text-slate-600 mt-1">Welcome to the AJU Admin Portal</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Total Documents</h3>
              <FileText className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.totalDocuments}</p>
            <p className="text-xs text-slate-500 mt-2">Indexed in knowledge base</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Total Queries</h3>
              <MessageSquare className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.totalQueries.toLocaleString()}</p>
            <p className="text-xs text-slate-500 mt-2">Answered by RAG engine</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Knowledge Gaps</h3>
              <AlertTriangle className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.knowledgeGaps}</p>
            <p className="text-xs text-slate-500 mt-2">Unresolved gaps</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Resolution Rate</h3>
              <Activity className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{stats.resolutionRate.toFixed(1)}%</p>
            <p className="text-xs text-slate-500 mt-2">Gaps resolved</p>
          </div>
        </div>
