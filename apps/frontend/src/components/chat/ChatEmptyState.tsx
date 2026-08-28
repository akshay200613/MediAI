'use client'

import React, { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  Stethoscope,
  UploadCloud,
  FileText,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { ragApi } from '@/lib/api/rag'

interface ChatEmptyStateProps {
  onSelectPrompt: (prompt: string) => void
  onDocumentIngested?: (docInfo: { title: string; chunks: number }) => void
  userName?: string
}

const clinicalPrompts = [
  {
    title: 'Patient Intake Protocols',
    prompt: 'Summarize standard patient intake and clinical triage protocols for emergency admissions.',
    category: 'Triage & Intake',
  },
  {
    title: 'Pharmacology & Contraindications',
    prompt: 'What are the primary contraindications and drug interactions for ACE inhibitors?',
    category: 'Pharmacology',
  },
  {
    title: 'Geriatric Hypertension Guidelines',
    prompt: 'Provide clinical practice guidelines for managing stage 2 hypertension in elderly patients.',
    category: 'Clinical Practice',
  },
  {
    title: 'Endocrine Diagnostic Criteria',
    prompt: 'Outline the diagnostic criteria and target HbA1c benchmarks for Type 2 Diabetes Mellitus.',
    category: 'Endocrinology',
  },
]

export const ChatEmptyState: React.FC<ChatEmptyStateProps> = ({ onSelectPrompt, onDocumentIngested, userName }) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<{ success: boolean; message: string } | null>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadStatus(null)

    try {
      const res = await ragApi.ingestDocument(file, file.name.replace(/\.[^/.]+$/, ''), 'clinical_guidelines')
      const chunksIndexed = res.data?.chunks_indexed || 0
      setUploadStatus({
        success: true,
        message: `Successfully ingested "${file.name}" (${chunksIndexed} knowledge chunks indexed).`,
      })
      onDocumentIngested?.({ title: file.name, chunks: chunksIndexed })
    } catch (err: any) {
      setUploadStatus({
        success: false,
        message: err.message || 'Failed to ingest document. Ensure standard PDF, DOCX, TXT, or JSON format.',
      })
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-slate-200 max-w-4xl mx-auto my-auto w-full">
      {/* Header Icon Badge */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="w-14 h-14 rounded-2xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 mb-5 shadow-lg shadow-teal-500/5"
      >
        <Stethoscope className="w-7 h-7" />
      </motion.div>

      {/* Main Title & Subtitle */}
      <motion.h1
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-2xl font-bold tracking-tight text-slate-100 text-center"
      >
        {userName ? (
          <>
            Hey <span className="text-teal-400">{userName}</span>! How can I help you today?
          </>
        ) : (
          'MediAI Clinical Assistant'
        )}
      </motion.h1>

      {/* RAG Knowledge Ingestion Section */}
      <motion.div
        initial={{ y: 15, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="w-full mt-7 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm"
      >
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-teal-400 border border-slate-700/60 shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="text-left">
              <h3 className="text-xs font-semibold text-slate-200">Expand Knowledge Base</h3>
              <p className="text-[11px] text-slate-400">
                Upload clinical guidelines, PDFs, or research notes for on-the-fly RAG search.
              </p>
            </div>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.txt,.md,.json"
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-teal-300 border border-slate-700 text-xs font-medium transition-colors shrink-0 disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-teal-400" />
                Indexing Document...
              </>
            ) : (
              <>
                <UploadCloud className="w-4 h-4 text-teal-400" />
                Upload Document
              </>
            )}
          </button>
        </div>

        {/* Upload Status Banner */}
        {uploadStatus && (
          <div
            className={`mt-3 p-2.5 rounded-lg text-xs flex items-center gap-2 ${
              uploadStatus.success
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border border-rose-500/20 text-rose-300'
            }`}
          >
            {uploadStatus.success ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            )}
            <span>{uploadStatus.message}</span>
          </div>
        )}
      </motion.div>

      {/* Starter Prompts Grid */}
      <div className="w-full mt-7">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="w-3.5 h-3.5 text-teal-400" />
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Suggested Clinical Queries
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {clinicalPrompts.map((item, index) => (
            <motion.button
              key={index}
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.25 + index * 0.05 }}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group text-left p-3.5 rounded-xl bg-slate-900/40 hover:bg-slate-800/70 border border-slate-800 hover:border-teal-500/40 transition-all flex flex-col justify-between cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono text-teal-400 px-1.5 py-0.5 rounded bg-teal-500/10 border border-teal-500/20">
                    {item.category}
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-teal-400 group-hover:translate-x-0.5 transition-all" />
                </div>
                <h4 className="text-xs font-medium text-slate-200 group-hover:text-slate-100">
                  {item.title}
                </h4>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                  "{item.prompt}"
                </p>
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Compliance Disclaimer */}
      <div className="mt-8 flex items-center gap-2 text-[11px] text-slate-500">
        <ShieldCheck className="w-3.5 h-3.5 text-teal-500/60" />
        <span>Clinical AI decisions should be reviewed against patient records and primary sources.</span>
      </div>
    </div>
  )
}
