'use client'
import { motion } from 'framer-motion'
import { Activity, Sparkles, Stethoscope, FileText, Pill } from 'lucide-react'
import { hoverChip, springBouncy } from '@/lib/motion'

interface ChatEmptyStateProps {
  onSelectPrompt: (prompt: string) => void
}

const suggestedPrompts = [
  {
    icon: Stethoscope,
    label: 'Differential Diagnosis',
    prompt: 'What are common differential diagnoses for acute right lower quadrant abdominal pain?',
  },
  {
    icon: FileText,
    label: 'Lab Interpretation',
    prompt: 'Explain what elevated HbA1c (7.8%) and microalbuminuria indicate in type 2 diabetes management.',
  },
  {
    icon: Pill,
    label: 'Medication Interactions',
    prompt: 'Are there any known contraindications between Metformin and Lisinopril for hypertensive patients?',
  },
  {
    icon: Sparkles,
    label: 'Clinical Summary',
    prompt: 'Provide a concise SOAP note template for a follow-up consultation on hypertension.',
  },
]

export function ChatEmptyState({ onSelectPrompt }: ChatEmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center max-w-2xl mx-auto my-auto">
      {/* MedAI Logo Mark */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={springBouncy}
        className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-glow mb-4 sm:mb-6"
      >
        <Activity className="w-7 h-7 sm:w-8 sm:h-8 text-white animate-breathe" />
      </motion.div>

      {/* Greeting Title & Subtitle */}
      <motion.h2
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-xl sm:text-3xl font-extrabold text-white tracking-tight mb-2"
      >
        How can MedAI assist your practice today?
      </motion.h2>

      <motion.p
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-xs sm:text-sm text-slate-400 max-w-md mb-6 sm:mb-8 leading-relaxed"
      >
        Ask clinical questions, analyze symptoms, or search clinic health records using our RAG-enabled medical AI.
      </motion.p>

      {/* Tappable Suggested Prompt Chips */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full"
      >
        {suggestedPrompts.map((item, idx) => {
          const Icon = item.icon
          return (
            <motion.button
              key={idx}
              whileHover={hoverChip}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSelectPrompt(item.prompt)}
              className="glass-card p-3.5 sm:p-4 text-left flex items-start gap-3 hover:border-teal-500/30 group transition-colors"
            >
              <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 group-hover:bg-teal-500 group-hover:text-white transition-colors flex-shrink-0">
                <Icon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white mb-0.5 group-hover:text-teal-300 transition-colors">
                  {item.label}
                </p>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {item.prompt}
                </p>
              </div>
            </motion.button>
          )
        })}
      </motion.div>
    </div>
  )
}
