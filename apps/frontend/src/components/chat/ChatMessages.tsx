'use client'
import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, Info, BookOpen } from 'lucide-react'
import { MessageItem } from '@/lib/hooks/useChatStore'
import { useStreamingText } from '@/lib/hooks/useStreamingText'
import { easeOutExpo } from '@/lib/motion'

function ChatMessageBubble({ message, isLast }: { message: MessageItem; isLast: boolean }) {
  const isUser = message.role === 'user'
  const isAi = message.role === 'assistant'

  // Character-by-character typewriter effect for the newest AI response
  const shouldStream = isAi && isLast && message.isStreaming
  const { displayedText, isDone } = useStreamingText(message.content, shouldStream)

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={easeOutExpo}
      className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {/* AI Logo Mark */}
      {isAi && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center text-white shadow-glow flex-shrink-0 mt-1">
          <Activity className="w-4 h-4" />
        </div>
      )}

      {/* Message Content Container */}
      <div className={`space-y-2 ${isUser ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
        {/* User Message Bubble */}
        {isUser && (
          <p className="text-xs sm:text-sm text-slate-100 leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        )}

        {/* AI Message (Bare text + MedAI Mark for maximum readability) */}
        {isAi && (
          <div className="space-y-3">
            {/* Callout styling if flagged */}
            {message.calloutType === 'amber' && (
              <div className="callout-amber">
                <Info className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-amber-200">
                  <span className="font-semibold">Clinical Caution:</span> Information retrieved from Knowledge Base should be correlated with direct patient examination.
                </div>
              </div>
            )}

            {message.calloutType === 'red' && (
              <div className="callout-red">
                <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs text-red-200">
                  <span className="font-semibold">Urgent Medical Triage Flagged:</span> Recommend immediate clinical evaluation.
                </div>
              </div>
            )}

            {/* Formatted Response Body with Streaming Cursor */}
            <div className="text-xs sm:text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
              {displayedText}
              {!isDone && <span className="typing-cursor" />}
            </div>

            {/* RAG Sources Citations */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-2 border-t border-white/5 space-y-1">
                <p className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                  <BookOpen className="w-3 h-3 text-teal-400" /> RAG Knowledge Sources:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {message.sources.map((src, i) => (
                    <span
                      key={i}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-surface-600/60 border border-white/5 text-slate-400"
                    >
                      {src.title || `Document Chunk #${i + 1}`} (Score: {(src.score * 100).toFixed(0)}%)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}

export function ChatMessages({
  messages,
  isGenerating,
}: {
  messages: MessageItem[]
  isGenerating: boolean
}) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isGenerating])

  return (
    <div className="w-full max-w-[720px] mx-auto px-4 py-6 space-y-6">
      {messages.map((msg, idx) => (
        <ChatMessageBubble key={msg.id} message={msg} isLast={idx === messages.length - 1} />
      ))}

      {/* Typing Indicator while waiting for initial chunk */}
      {isGenerating && messages[messages.length - 1]?.role === 'user' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3"
        >
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center text-white shadow-glow flex-shrink-0">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div className="chat-bubble-ai">
            <div className="bounce-dots py-1">
              <span />
              <span />
              <span />
            </div>
          </div>
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
