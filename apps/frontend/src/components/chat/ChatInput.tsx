'use client'

import React, { useState, useRef, useEffect } from 'react'
import { ArrowUp, UploadCloud, Loader2, Square } from 'lucide-react'
import { ragApi } from '@/lib/api/rag'
import { useChatStore } from '@/lib/hooks/useChatStore'

interface ChatInputProps {
  onSend: (text: string) => void
  isGenerating?: boolean
  onDocumentUploaded?: () => void
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, isGenerating, onDocumentUploaded }) => {
  const { stopGeneration } = useChatStore()
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
    <div className="p-3 sm:p-4 border-t border-slate-800/80 bg-slate-950/80 backdrop-blur-md relative z-10 font-sans">
      {/* Upload Notification Chip */}
      {uploadNotice && (
        <div className="max-w-3xl mx-auto mb-2 p-2 rounded-lg bg-slate-900 border border-teal-500/30 text-xs text-teal-300 flex items-center justify-between">
          <span className="truncate">{uploadNotice}</span>
          <button
            onClick={() => setUploadNotice(null)}
            className="text-slate-400 hover:text-slate-200 text-xs pl-2"
          >
            Dismiss
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative">
        <div className="flex items-end gap-2 p-2 rounded-2xl bg-slate-900 border border-slate-800 focus-within:border-teal-500/50 shadow-xl shadow-slate-950/50 transition-all">
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
            className="p-2 rounded-xl text-slate-400 hover:text-teal-300 hover:bg-slate-800 transition-colors shrink-0 disabled:opacity-50"
            title="Upload document for RAG ingestion"
          >
            {isUploading ? (
              <Loader2 className="w-5 h-5 animate-spin text-teal-400" />
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
            placeholder="Ask MediAI clinical assistant or query ingested documents..."
            className="flex-1 bg-transparent text-xs sm:text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none py-1.5 px-1 max-h-44 scrollbar-thin"
          />

          {/* Submit Action Button */}
          {isGenerating ? (
            <button
              type="button"
              onClick={stopGeneration}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium shadow-md transition-all shrink-0"
              title="Stop generating"
            >
              <Square className="w-5 h-5 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!text.trim()}
              className="p-2 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-medium shadow-md shadow-teal-900/20 transition-all shrink-0 disabled:opacity-40 disabled:hover:bg-teal-600 disabled:cursor-not-allowed"
              title="Send query (Enter)"
            >
              <ArrowUp className="w-5 h-5" />
            </button>
          )}
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
