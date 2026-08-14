'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, FileText, Database, Sparkles, Layers, Quote, ShieldCheck } from 'lucide-react'
import type { Citation, RetrievalMethod } from '@/types/chat'

interface CitationPanelProps {
  isOpen: boolean
  onClose: () => void
  citations: Citation[]
  selectedCitationId?: string | null
  onSelectCitation?: (id: string) => void
}

const methodConfig: Record<
  RetrievalMethod,
  { label: string; icon: React.ElementType; badgeClass: string; borderClass: string }
> = {
  vector: {
    label: 'Vector Search',
    icon: Sparkles,
    badgeClass: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    borderClass: 'border-l-indigo-500',
  },
  keyword: {
    label: 'BM25 Keyword',
    icon: Database,
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    borderClass: 'border-l-amber-500',
  },
  hybrid: {
    label: 'Hybrid RRF',
    icon: Layers,
    badgeClass: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
    borderClass: 'border-l-teal-500',
  },
}

export const CitationPanel: React.FC<CitationPanelProps> = ({
  isOpen,
  onClose,
  citations,
  selectedCitationId,
  onSelectCitation,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            aria-hidden="true"
          />

          {/* Slide-over panel */}
          <motion.aside
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 280 }}
            className="fixed right-0 top-0 bottom-0 w-full sm:w-[420px] bg-slate-900 border-l border-slate-800/80 shadow-2xl z-50 flex flex-col min-h-screen text-slate-200"
            role="dialog"
            aria-label="Clinical Source Citations"
          >
            {/* Panel Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 backdrop-blur">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-100">Clinical Knowledge Sources</h3>
                  <p className="text-xs text-slate-400">
                    {citations.length} RAG retrieval {citations.length === 1 ? 'match' : 'matches'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
                aria-label="Close citations panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Citations List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {citations.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  No source citations linked to this query response.
                </div>
              ) : (
                citations.map((cite, index) => {
                  const isSelected = selectedCitationId === cite.id
                  const methodInfo = methodConfig[cite.retrievalMethod] || methodConfig.hybrid
                  const MethodIcon = methodInfo.icon
                  const matchScorePct = Math.round((cite.score || 0.85) * 100)

                  return (
                    <motion.div
                      key={cite.id || index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      onClick={() => onSelectCitation?.(cite.id)}
                      className={`group p-4 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-800/90 border-teal-500/40 shadow-lg shadow-teal-500/5'
                          : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
                      } ${methodInfo.borderClass} border-l-4`}
                    >
                      {/* Top Bar: Doc Name & Ref Number */}
                      <div className="flex items-start justify-between gap-3 mb-2.5">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-4 h-4 text-teal-400 shrink-0" />
                          <span className="font-medium text-xs text-slate-200 truncate" title={cite.documentName}>
                            [{index + 1}] {cite.documentName}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-teal-300 border border-slate-700 shrink-0">
                          {matchScorePct}% Match
                        </span>
                      </div>

                      {/* Excerpt Body */}
                      <div className="relative pl-3 pr-2 py-2 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs text-slate-300 leading-relaxed font-sans mb-3">
                        <Quote className="w-3.5 h-3.5 text-slate-600 absolute -top-1.5 left-2 bg-slate-950 px-0.5" />
                        <p className="line-clamp-4 italic text-slate-300/90 pt-1">
                          "{cite.excerpt}"
                        </p>
                      </div>

                      {/* Method Tag Footer */}
                      <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/60 pt-2.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-[10px] font-medium ${methodInfo.badgeClass}`}
                        >
                          <MethodIcon className="w-3 h-3" />
                          {methodInfo.label}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          ID: {cite.id.slice(0, 8)}
                        </span>
                      </div>
                    </motion.div>
                  )
                })
              )}
            </div>

            {/* Panel Footer */}
            <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 text-center">
              <p className="text-[11px] text-slate-500">
                Sources retrieved via MediAI Qdrant + BM25 Hybrid Pipeline
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
