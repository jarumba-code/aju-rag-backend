"use client";

import { useState, useEffect } from "react";
import AdminShell from "@/components/AdminShell";
import { BarChart3, TrendingUp, Users, MessageSquare } from "lucide-react";

interface AnalyticsData {
  totalQueries: number;
  activeUsers: number;
  avgResponseTime: string;
  satisfaction: number;
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setData({
        totalQueries: 15420,
        activeUsers: 342,
        avgResponseTime: "1.2s",
        satisfaction: 4.6,
      });
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <AdminShell>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-600">Loading analytics...</p>
          </div>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Analytics & Reports</h1>
          <p className="text-sm text-slate-600 mt-1">Monitor portal performance and user engagement</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Total Queries</h3>
              <MessageSquare className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{data?.totalQueries.toLocaleString()}</p>
            <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp size={14} />
              +12.5% from last month
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Active Users</h3>
              <Users className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{data?.activeUsers}</p>
            <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
              <TrendingUp size={14} />
              +8.2% from last week
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Avg Response Time</h3>
              <BarChart3 className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{data?.avgResponseTime}</p>
            <p className="text-xs text-green-600 mt-2">-0.3s improvement</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Satisfaction</h3>
              <TrendingUp className="text-gold-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">{data?.satisfaction}/5</p>
            <p className="text-xs text-green-600 mt-2">+0.2 from last month</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Query Trends</h2>
          <div className="h-64 flex items-center justify-center border-2 border-dashed border-slate-300 rounded-lg">
            <p className="text-slate-500">Chart visualization will be displayed here</p>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
