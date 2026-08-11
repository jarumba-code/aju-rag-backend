"use client";

import AdminShell from "@/components/AdminShell";
import { AlertTriangle, Lightbulb, CheckCircle } from "lucide-react";

interface Gap {
  id: string;
  topic: string;
  question: string;
  frequency: number;
  status: "open" | "in_progress" | "resolved";
}

const gaps: Gap[] = [
  { id: "1", topic: "Admission Requirements", question: "What are the minimum JAMB scores?", frequency: 45, status: "open" },
  { id: "2", topic: "Hostel Accommodation", question: "How do I apply for hostel?", frequency: 32, status: "in_progress" },
  { id: "3", topic: "Scholarship", question: "What scholarships are available?", frequency: 28, status: "resolved" },
];

const getStatusIcon = (status: Gap["status"]) => {
  switch (status) {
    case "open": return <AlertTriangle className="text-red-500" size={20} />;
    case "in_progress": return <Lightbulb className="text-yellow-500" size={20} />;
    case "resolved": return <CheckCircle className="text-green-500" size={20} />;
  }
};

export default function GapsPage() {
  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Gaps & Improvements</h1>
          <p className="text-sm text-slate-600 mt-1">Identify and address knowledge gaps in your portal</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Open Gaps</h3>
              <AlertTriangle className="text-red-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">12</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">In Progress</h3>
              <Lightbulb className="text-yellow-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">8</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-slate-600">Resolved</h3>
              <CheckCircle className="text-green-500" size={20} />
            </div>
            <p className="text-3xl font-bold text-navy">45</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Identified Gaps</h2>
          <div className="space-y-4">
            {gaps.map((gap) => (
              <div key={gap.id} className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50">
                <div className="flex items-start gap-4">
                  {getStatusIcon(gap.status)}
                  <div>
                    <h3 className="font-semibold text-slate-900">{gap.topic}</h3>
                    <p className="text-sm text-slate-600 mt-1">{gap.question}</p>
                    <p className="text-xs text-slate-500 mt-2">Asked {gap.frequency} times</p>
                  </div>
                </div>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                  gap.status === "open" ? "bg-red-100 text-red-800" :
                  gap.status === "in_progress" ? "bg-yellow-100 text-yellow-800" :
                  "bg-green-100 text-green-800"
                }`}>
                  {gap.status.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
