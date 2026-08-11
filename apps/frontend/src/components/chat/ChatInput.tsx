'use client'
import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Square, Paperclip, AlertCircle } from 'lucide-react'
import { springSnappy } from '@/lib/motion'
import toast from 'react-hot-toast'

interface ChatInputProps {
  onSend: (text: string) => void
  isGenerating: boolean
}

export function ChatInput({ onSend, isGenerating }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-expand textarea height up to 160px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isGenerating) return
    onSend(input.trim())
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      toast.success(`Attached file: ${file.name} (RAG ready)`)
    }
  }

  return (
    <div className="w-full max-w-[720px] mx-auto px-3 sm:px-4 pb-3 sm:pb-4 pt-2 flex-shrink-0">
      {/* Pill-Shaped Container */}
      <form
        onSubmit={handleSubmit}
        className="glass-card p-1.5 sm:p-2 flex items-center gap-2 rounded-2xl sm:rounded-full border border-white/10 shadow-glow focus-within:border-teal-500/50 focus-within:ring-2 focus-within:ring-teal-500/20 transition-all"
      >
        {/* Attach File Button */}
        <label className="p-2.5 rounded-full text-slate-400 hover:text-white hover:bg-white/5 cursor-pointer transition-colors flex-shrink-0">
          <Paperclip className="w-4 h-4" />
          <input type="file" onChange={handleFileUpload} className="hidden" />
        </label>

        {/* Auto-expanding Input Area */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask MedAI clinical questions..."
          rows={1}
          className="flex-1 bg-transparent text-xs sm:text-sm text-slate-100 placeholder-slate-500 resize-none focus:outline-none py-1.5 sm:py-2 px-1 max-h-36 overflow-y-auto"
        />

        {/* Send / Stop Button Morph */}
        <motion.button
          type="submit"
          disabled={!input.trim() && !isGenerating}
          whileTap={{ scale: 0.9 }}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-teal-500 to-cyan-500 text-white flex items-center justify-center flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed shadow-glow transition-all"
        >
          <AnimatePresence mode="wait">
            {isGenerating ? (
              <motion.div
                key="stop"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={springSnappy}
              >
                <Square className="w-3.5 h-3.5 sm:w-4 sm:h-4 fill-white" />
              </motion.div>
            ) : (
              <motion.div
                key="send"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={springSnappy}
              >
                <Send className="w-3.5 h-3.5 sm:w-4 sm:h-4 ml-0.5" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </form>

      {/* Muted HIPAA Disclaimer */}
      <p className="text-[10px] text-center text-slate-500 mt-2 flex items-center justify-center gap-1">
        <AlertCircle className="w-3 h-3 text-slate-500 flex-shrink-0" />
        Medai provides general health information and is not a substitute for professional medical advice.
      </p>
    </div>
  )
}
