'use client'

import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User,
  Stethoscope,
  FileText,
  Search,
  Layers,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'
import type { ChatMessage, Citation } from '@/types/chat'

import { ActionCards } from './ActionCards'

interface ChatMessagesProps {
  messages: ChatMessage[]
  isGenerating?: boolean
  userName?: string
  onSelectCitation?: (citationId: string, citations: Citation[]) => void
  onRetryMessage?: (messageContent: string) => void
  onActionSelected?: (messageContent: string) => void
}

export const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  isGenerating,
  userName,
  onSelectCitation,
  onRetryMessage,
  onActionSelected,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isGenerating])

  // Simple Markdown Formatter Helper
  const renderMarkdown = (text: string) => {
    if (!text) return null

    // Split into paragraphs / lines
    const lines = text.split('\n')
    return (
      <div className="space-y-2 text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
        {lines.map((line, idx) => {
          if (!line.trim()) return <div key={idx} className="h-1.5" />

          // Headers
          if (line.startsWith('### ')) {
            return (
              <h4 key={idx} className="font-semibold text-sm text-slate-100 mt-3 mb-1">
                {line.replace('### ', '')}
              </h4>
            )
          }
          if (line.startsWith('## ')) {
            return (
              <h3 key={idx} className="font-semibold text-base text-slate-100 mt-4 mb-1 border-b border-slate-800 pb-1">
                {line.replace('## ', '')}
              </h3>
            )
          }

          // Bullet points
          if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
            const cleanText = line.trim().replace(/^[-*]\s+/, '')
            return (
              <div key={idx} className="flex items-start gap-2 pl-2">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-400 shrink-0 mt-1.5" />
                <span>{formatInlineFormatting(cleanText)}</span>
              </div>
            )
          }

          // Default text line
          return <p key={idx}>{formatInlineFormatting(line)}</p>
        })}
      </div>
    )
  }

  // Format bold / inline code
  const formatInlineFormatting = (str: string) => {
    // Bold **text**
    const parts = str.split(/(\*\*.*?\*\*|`.*?`)/g)
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-slate-100">
            {part.slice(2, -2)}
          </strong>
        )
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-teal-300 font-mono text-xs">
            {part.slice(1, -1)}
          </code>
        )
      }
      return <span key={i}>{part}</span>
    })
  }

  // Helper to format any arbitrary JSON object/array into clean, human-readable text
  const formatJsonToReadableText = (obj: any): string => {
    if (obj === null || obj === undefined) return ''
    if (typeof obj === 'string') {
      const trimmed = obj.trim()
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        try {
          const parsed = JSON.parse(trimmed)
          return formatJsonToReadableText(parsed)
        } catch {
          return obj
        }
      }
      return obj
    }
    if (typeof obj === 'number' || typeof obj === 'boolean') {
      return String(obj)
    }
    if (Array.isArray(obj)) {
      return obj
        .map((item) => {
          if (typeof item === 'object' && item !== null) {
            return `• ${formatJsonToReadableText(item).replace(/\n/g, ' ')}`
          }
          return `• ${item}`
        })
        .join('\n')
    }
    if (typeof obj === 'object') {
      // If object has a primary text/response field, return it directly
      const primaryKeys = ['response', 'message', 'answer', 'reply', 'content', 'text', 'summary', 'details']
      for (const pk of primaryKeys) {
        if (obj[pk] && typeof obj[pk] === 'string' && obj[pk].trim().length > 0) {
          return obj[pk].trim()
        }
      }

      // Format key-values into clean bulleted text
      const lines: string[] = []
      for (const [k, v] of Object.entries(obj)) {
        if (k.startsWith('__') || k === 'action' || v === null || v === undefined) continue
        const formattedKey = k
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase())
        if (typeof v === 'object') {
          lines.push(`**${formattedKey}:**\n${formatJsonToReadableText(v)}`)
        } else {
          lines.push(`**${formattedKey}:** ${v}`)
        }
      }
      return lines.join('\n\n')
    }
    return String(obj)
  }

  // Robust JSON stripper and Action Card extractor
  const parseContentAndAction = (content: string, isUser: boolean) => {
    if (!content) return { text: '', actionData: null }

    // 1. User messages: decode JSON action payloads into clean human-readable text
    if (isUser) {
      try {
        const trimmed = content.trim()
        if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
          const payload = JSON.parse(trimmed)
          if (payload.__action === 'select_slot') {
            return {
              text: `Selected slot ${payload.selected_slot} on ${payload.date} with ${payload.doctor || 'doctor'}.`,
              actionData: null,
            }
          }
          if (payload.__action === 'confirm_booking') {
            return {
              text: `Confirmed appointment with ${payload.doctor || 'doctor'} on ${payload.date} at ${payload.time}.`,
              actionData: null,
            }
          }
          if (payload.__action === 'cancel_booking_flow') {
            return {
              text: `Cancelled booking flow.`,
              actionData: null,
            }
          }
          // Fallback user JSON format
          return {
            text: formatJsonToReadableText(payload),
            actionData: null,
          }
        }
      } catch {}
      return { text: content, actionData: null }
    }

    // 2. Assistant messages: extract ANY json block (codefence ```json ... ```, ``` ... ```, or raw { "action": ... })
    let actionData: any = null
    let cleaned = content

    // Match markdown codeblocks with ```json ... ``` or ``` ... ```
    const codeBlockRegex = /```(?:json)?\s*([\s\S]*?)\s*```/gi
    cleaned = cleaned.replace(codeBlockRegex, (fullMatch, rawInner) => {
      const trimmed = (rawInner || '').trim()
      if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
        try {
          const parsed = JSON.parse(trimmed)
          if (parsed && typeof parsed === 'object' && parsed.action) {
            actionData = parsed
            return '' // Remove action JSON block from rendered text
          }
          // For non-action JSON blocks, convert to clean readable text
          return formatJsonToReadableText(parsed)
        } catch {
          return fullMatch
        }
      }
      return fullMatch
    }).trim()

    // If whole content or substring is a standalone JSON object
    if (!actionData) {
      const trimmedCleaned = cleaned.trim()
      if ((trimmedCleaned.startsWith('{') && trimmedCleaned.endsWith('}')) || (trimmedCleaned.startsWith('[') && trimmedCleaned.endsWith(']'))) {
        try {
          const parsed = JSON.parse(trimmedCleaned)
          if (parsed && typeof parsed === 'object' && parsed.action) {
            actionData = parsed
            cleaned = ''
          } else {
            cleaned = formatJsonToReadableText(parsed)
          }
        } catch {}
      } else {
        const rawJsonMatch = cleaned.match(/(\{[\s\r\n]*"action"[\s\S]*?\})/i)
        if (rawJsonMatch) {
          try {
            const parsed = JSON.parse(rawJsonMatch[1])
            if (parsed && parsed.action) {
              actionData = parsed
              cleaned = cleaned.replace(rawJsonMatch[0], '').trim()
            }
          } catch {}
        }
      }
    }

    // Ensure any leftover backtick blocks like ```json or ``` are cleanly stripped
    cleaned = cleaned.replace(/```(?:json)?/gi, '').replace(/```/g, '').trim()

    return { text: cleaned, actionData }
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 scroll-smooth"
      role="log"
      aria-live="polite"
      aria-label="Clinical chat trajectory"
    >
      <AnimatePresence initial={false}>
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user'

          return (
            <motion.div
              key={msg.id || index}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex items-start gap-3 max-w-3xl ${isUser ? 'ml-auto justify-end' : 'mr-auto'}`}
            >
              {/* Assistant Avatar */}
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shrink-0 mt-0.5">
                  <Stethoscope className="w-4 h-4" />
                </div>
              )}

              {/* Message Content Bubble */}
              <div className="flex flex-col min-w-0 max-w-2xl">
                {/* Role Label & Timestamp */}
                <div className={`flex items-center gap-2 mb-1 text-[11px] text-slate-400 ${isUser ? 'justify-end' : ''}`}>
                  <span className="font-medium text-slate-300">
                    {isUser ? (userName || 'User') : 'MediAI Assistant'}
                  </span>
                  <span className="text-slate-400 text-[10px]">
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                {/* Bubble Body */}
                <div
                  className={`p-4 rounded-2xl ${
                    isUser
                      ? 'bg-slate-800 border border-slate-700/80 text-slate-100 rounded-tr-sm'
                      : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-sm shadow-xl shadow-slate-950/40'
                  } ${
                    msg.calloutType === 'red'
                      ? 'border-l-4 border-l-rose-500'
                      : msg.calloutType === 'amber'
                      ? 'border-l-4 border-l-amber-500'
                      : ''
                  }`}
                >
                  {/* Typing / streaming indicator if content is still loading */}
                  {!isUser && msg.isStreaming && !msg.content && (
                    <div className="flex items-center gap-1.5 py-1">
                      <span className="w-2 h-2 rounded-full bg-teal-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 rounded-full bg-teal-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 rounded-full bg-teal-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}

                  {/* Render Text Content & Action Cards (No raw JSON shown) */}
                  {(() => {
                    const { text, actionData } = parseContentAndAction(msg.content, isUser);
                    return (
                      <>
                        {text && renderMarkdown(text)}
                        {actionData && (
                          <ActionCards actionData={actionData} onAction={(m) => onActionSelected?.(m)} />
                        )}
                      </>
                    )
                  })()}

                  {/* Streaming Pulse Cursor */}
                  {msg.isStreaming && (
                    <span className="inline-block w-1.5 h-4 bg-teal-400 animate-pulse ml-1 align-middle rounded" />
                  )}

                  {/* Error Retry Banner */}
                  {msg.error && (
                    <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                        <span>{msg.error}</span>
                      </div>
                      {onRetryMessage && (
                        <button
                          onClick={() => onRetryMessage(messages[index - 1]?.content || '')}
                          className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-[11px] font-medium inline-flex items-center gap-1 shrink-0"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Retry
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* User Avatar */}
              {isUser && (
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
