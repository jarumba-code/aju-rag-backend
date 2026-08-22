"use client";

import React, { useState, useEffect } from "react";
import { FileText, Trash2, Search, Upload } from "lucide-react";
import { adminDocuments, adminDeleteDocument, DocumentRecord } from "@/lib/adminApi";
import Link from "next/link";

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const loadDocs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminDocuments();
      setDocuments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;
    try {
      await adminDeleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete document.");
    }
  };

  const filteredDocs = documents.filter(
    (doc) =>
      doc.filename.toLowerCase().includes(search.toLowerCase()) ||
      (doc.department && doc.department.toLowerCase().includes(search.toLowerCase())) ||
      (doc.doc_type && doc.doc_type.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-navy aju-serif">Content Management</h1>
            <p className="text-sm text-slate-600 mt-1">
              View and manage indexed institutional documents
            </p>
          </div>
          <Link
            href="/admin/upload"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-gold-600 text-white font-medium rounded-lg hover:bg-gold-700 transition-colors shadow-sm"
          >
            <Upload size={18} />
            <span>Upload Document</span>
          </Link>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 flex items-center gap-3">
          <Search size={18} className="text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by filename, department, or document type..."
            className="flex-1 text-sm outline-none text-slate-800 placeholder:text-slate-400"
          />
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="w-10 h-10 border-4 border-gold-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 border border-red-200 rounded-xl text-center">
            <p className="text-red-700 text-sm mb-3">{error}</p>
            <button
              onClick={loadDocs}
              className="px-4 py-2 bg-gold-600 text-white rounded-lg text-sm hover:bg-gold-700"
            >
              Retry
            </button>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-navy">No documents found</h3>
            <p className="text-sm text-slate-500 mt-1">
              {search ? "No documents match your search query." : "No institutional documents have been ingested yet."}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-700">
                <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3">Filename</th>
                    <th className="px-6 py-3">Department</th>
                    <th className="px-6 py-3">Type</th>
                    <th className="px-6 py-3">Chunks</th>
                    <th className="px-6 py-3">Created</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-slate-900 flex items-center gap-2">
                        <FileText size={16} className="text-gold-600 shrink-0" />
                        <span className="truncate max-w-xs">{doc.filename}</span>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{doc.department || "General"}</td>
                      <td className="px-6 py-4 text-slate-600">{doc.doc_type || "Document"}</td>
                      <td className="px-6 py-4 text-slate-600">{doc.chunk_count}</td>
                      <td className="px-6 py-4 text-slate-500 text-xs">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString("en-NG") : "N/A"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="text-red-600 hover:text-red-800 p-1.5 rounded-lg hover:bg-red-50 transition-colors"
                          title="Delete document"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

  );
}
