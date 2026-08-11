"use client";

import { useState } from "react";
import AdminShell from "@/components/AdminShell";
import { Upload, FileText, X, CheckCircle } from "lucide-react";

export default function UploadPage() {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const files = Array.from(e.dataTransfer.files);
    setUploadedFiles(files.map(f => f.name));
  };

  return (
    <AdminShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-navy aju-serif">Upload Document</h1>
          <p className="text-sm text-slate-600 mt-1">Add new documents to the knowledge base</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              dragActive ? "border-gold-500 bg-gold-50" : "border-slate-300"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto text-slate-400 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-navy mb-2">Drop files here or click to upload</h3>
            <p className="text-sm text-slate-600 mb-4">Support for PDF, DOCX, TXT files up to 10MB</p>
            <button className="inline-flex items-center gap-2 px-4 py-2 bg-gold-600 text-white rounded-lg hover:bg-gold-700">
              <FileText size={18} />
              Browse Files
            </button>
          </div>

          {uploadedFiles.length > 0 && (
            <div className="mt-6 space-y-2">
              <h3 className="font-semibold text-slate-900">Uploaded Files:</h3>
              {uploadedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="text-green-600" size={20} />
                    <span className="text-sm font-medium text-slate-900">{file}</span>
                  </div>
                  <button className="text-slate-400 hover:text-slate-600">
                    <X size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  );
}
