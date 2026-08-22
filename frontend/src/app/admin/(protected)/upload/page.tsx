"use client";

import { useState, useRef } from "react";
import { Upload, FileText, X, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { adminUploadDocument } from "@/lib/adminApi";
import Link from "next/link";

interface UploadResult {
  filename: string;
  document_id: string;
  department?: string;
  doc_type?: string;
}

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [department, setDepartment] = useState("");
  const [docType, setDocType] = useState("pdf");
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") {
      setSelectedFile(file);
      setResult(null);
      setError(null);
    } else if (file) {
      setError("Only PDF files are supported.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await adminUploadDocument(
        selectedFile,
        department.trim() || undefined,
        docType || undefined
      );
      setResult({
        filename: res.filename,
        document_id: res.document_id,
        department: res.department,
        doc_type: res.doc_type,
      });
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setDepartment("");
      setDocType("pdf");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-navy aju-serif">Upload Document</h1>
        <p className="text-sm text-slate-600 mt-1">Add new PDF documents to the knowledge base</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        {/* Drop zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
            dragActive
              ? "border-gold-500 bg-gold-50"
              : selectedFile
              ? "border-green-400 bg-green-50"
              : "border-slate-300 hover:border-gold-400 hover:bg-slate-50"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !selectedFile && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          {selectedFile ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="text-green-600" size={32} />
              <div className="text-left">
                <p className="font-semibold text-slate-900">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); handleClearFile(); }}
                className="ml-4 p-1 text-slate-400 hover:text-red-500 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
          ) : (
            <>
              <Upload className="mx-auto text-slate-400 mb-4" size={48} />
              <h3 className="text-lg font-semibold text-navy mb-2">Drop a PDF here or click to browse</h3>
              <p className="text-sm text-slate-500">Only PDF files are supported. Max 50 MB.</p>
            </>
          )}
        </div>

        {/* Metadata fields */}
        {selectedFile && (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Department <span className="text-slate-400">(optional)</span>
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Software Engineering"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Document Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gold-500"
              >
                <option value="pdf">PDF</option>
                <option value="handbook">Handbook</option>
                <option value="policy">Policy</option>
                <option value="prospectus">Prospectus</option>
                <option value="calendar">Academic Calendar</option>
              </select>
            </div>
          </div>
        )}

        {/* Upload button */}
        {selectedFile && (
          <div className="mt-6">
            <button
              id="upload-submit-btn"
              onClick={handleUpload}
              disabled={uploading}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gold-600 text-white font-semibold rounded-lg hover:bg-gold-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Uploading &amp; Indexing…
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload to Knowledge Base
                </>
              )}
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="mt-4 flex items-start gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-sm font-semibold text-green-800">Document uploaded successfully!</p>
              <p className="text-xs text-green-700 mt-1">
                <strong>{result.filename}</strong> has been indexed into the knowledge base.
              </p>
              {result.department && (
                <p className="text-xs text-green-600">Department: {result.department}</p>
              )}
              <Link
                href="/admin/documents"
                className="inline-block mt-3 text-xs font-medium text-green-700 underline hover:text-green-900"
              >
                View in Documents →
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
