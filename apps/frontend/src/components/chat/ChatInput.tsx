'use client'

import React, { useState, useRef, useEffect } from 'react'
import { ArrowUp, UploadCloud, Loader2, FileText, CheckCircle2, AlertCircle } from 'lucide-react'
import { ragApi } from '@/lib/api/rag'

interface ChatInputProps {
  onSend: (text: string) => void
  isGenerating?: boolean
  onDocumentUploaded?: () => void
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, isGenerating, onDocumentUploaded }) => {
  const [text, setText] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadNotice, setUploadNotice] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
    }
  }, [text])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!text.trim() || isGenerating) return
    onSend(text.trim())
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleFileIngest = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadNotice(null)

    try {
      const res = await ragApi.ingestDocument(file, file.name.replace(/\.[^/.]+$/, ''), 'clinical_doc')
      const chunks = res.data?.chunks_indexed || 0
      setUploadNotice(`Indexed "${file.name}" (${chunks} chunks). Ready for RAG query!`)
      onDocumentUploaded?.()
    } catch (err: any) {
      setUploadNotice(`Failed to upload: ${err.message || 'Check file format'}`)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <div className="p-3 sm:p-4 border-t border-primary-light/20 bg-primary-dark/80 backdrop-blur-md relative z-10 font-sans">
      {/* Upload Notification Chip */}
      {uploadNotice && (
        <div className="max-w-3xl mx-auto mb-2 p-2 rounded-lg bg-primary-medium border border-accent-gold/30 text-xs text-accent-gold flex items-center justify-between">
          <span className="truncate">{uploadNotice}</span>
          <button
            onClick={() => setUploadNotice(null)}
            className="text-text-medium hover:text-text-light text-xs pl-2"
          >
            Dismiss
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
        <div className="flex items-center gap-2 p-2 rounded-full bg-primary-medium/50 backdrop-blur-xl border border-primary-light/30 focus-within:border-accent-light focus-within:ring-2 focus-within:ring-accent-gold/50 shadow-[0_8px_32px_rgb(0,0,0,0.2)] shadow-primary-dark/20 transition-all duration-300">
          {/* File Upload Affordance */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileIngest}
            accept=".pdf,.docx,.txt,.md,.json"
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isGenerating}
            className="p-3 rounded-full text-accent-gold hover:text-primary-dark hover:bg-accent-gold/80 transition-all shrink-0 disabled:opacity-50"
            title="Upload document for RAG ingestion"
          >
            {isUploading ? (
              <Loader2 className="w-5 h-5 animate-spin text-accent-light" />
            ) : (
              <UploadCloud className="w-5 h-5" />
            )}
          </button>

          {/* Auto-resizing Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask MediAI clinical assistant..."
            className="flex-1 bg-transparent text-sm text-text-light placeholder-text-medium resize-none focus:outline-none py-2.5 px-2 max-h-44 scrollbar-thin self-center"
          />

          {/* Submit Action Button */}
          <button
            type="submit"
            disabled={!text.trim() || isGenerating}
            className="p-3 rounded-full bg-gradient-to-r from-accent-gold to-accent-light hover:scale-[1.05] active:scale-95 text-primary-dark font-semibold shadow-lg transition-all shrink-0 disabled:opacity-40 disabled:from-primary-light disabled:to-primary-medium disabled:cursor-not-allowed"
            title="Send query (Enter)"
          >
            {isGenerating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <ArrowUp className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Footer Shortcut & Disclaimer */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 px-2">
          <span>
            Press <kbd className="px-1 py-0.5 font-mono text-[10px] bg-slate-900 border border-slate-800 rounded">Enter</kbd> to send, <kbd className="px-1 py-0.5 font-mono text-[10px] bg-slate-900 border border-slate-800 rounded">Shift+Enter</kbd> for newline
          </span>
          <span className="hidden sm:inline-block">MediAI RAG Hybrid Engine v0.1</span>
        </div>
      </form>
    </div>
  )
}
