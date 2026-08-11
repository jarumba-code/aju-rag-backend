"use client";

import AdminShell from "@/components/AdminShell";
import { Lightbulb, Plus, Check, X } from "lucide-react";

interface SuggestedQuestion {
  id: string;
  question: string;
  category: string;
  votes: number;
  status: "pending" | "approved" | "rejected";
}

const questions: SuggestedQuestion[] = [
  { id: "1", question: "What is the admission deadline for 2025/2026 session?", category: "Admissions", votes: 23, status: "pending" },
  { id: "2", question: "How do I check my examination results?", category: "Academics", votes: 18, status: "approved" },
  { id: "3", question: "What are the hostel fees per semester?", category: "Hostel", votes: 15, status: "pending" },
];

export default function SuggestedQuestionsPage() {
  return (
    <AdminShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-navy aju-serif">Suggested Questions</h1>
            <p className="text-sm text-slate-600 mt-1">Review and manage user-submitted questions</p>
          </div>
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-gold-600 text-white rounded-lg hover:bg-gold-700">
            <Plus size={18} />
            Add Question
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="text-sm font-medium text-slate-600 mb-2">Pending Review</h3>
            <p className="text-3xl font-bold text-yellow-600">5</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="text-sm font-medium text-slate-600 mb-2">Approved</h3>
            <p className="text-3xl font-bold text-green-600">128</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="text-sm font-medium text-slate-600 mb-2">Rejected</h3>
            <p className="text-3xl font-bold text-red-600">12</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-navy mb-4">Suggested Questions</h2>
          <div className="space-y-4">
            {questions.map((q) => (
              <div key={q.id} className="flex items-start justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50">
                <div className="flex items-start gap-4 flex-1">
                  <Lightbulb className="text-gold-500 mt-1" size={20} />
                  <div className="flex-1">
                    <p className="text-slate-900 font-medium">{q.question}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">{q.category}</span>
                      <span className="text-xs text-slate-500">{q.votes} votes</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  {q.status === "pending" && (
                    <>
                      <button className="p-2 text-green-600 hover:bg-green-50 rounded-lg">
                        <Check size={18} />
                      </button>
                      <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                        <X size={18} />
                      </button>
                    </>
                  )}
                  <span className={`text-xs px-3 py-1 rounded-full font-medium ${
                    q.status === "pending" ? "bg-yellow-100 text-yellow-800" :
                    q.status === "approved" ? "bg-green-100 text-green-800" :
                    "bg-red-100 text-red-800"
                  }`}>
                    {q.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
