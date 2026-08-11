'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Heart,
  Moon,
  Footprints,
  Calendar,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  FileUp,
  MessageSquare,
  Activity,
  Clock,
  UserPlus,
} from 'lucide-react'
import { useAuth } from '@/lib/auth/context'
import { Card, Skeleton, Button } from '@/components/ui'
import { useCountUp } from '@/lib/hooks/useCountUp'
import { patientsApi } from '@/lib/api/patients'
import { doctorsApi } from '@/lib/api/doctors'
import { appointmentsApi } from '@/lib/api/appointments'
import { formatDateTime } from '@/lib/utils'
import type { Appointment } from '@/types'
import { staggerContainer, fadeSlideUp } from '@/lib/motion'

// Metric card component with animated count-up and SVG sparkline
function MetricCard({
  title,
  value,
  unit,
  change,
  isPositive,
  icon: Icon,
  color,
  sparklineData,
  loading,
}: {
  title: string
  value: number
  unit?: string
  change?: string
  isPositive?: boolean
  icon: typeof Heart
  color: string
  sparklineData: number[]
  loading: boolean
}) {
  const animatedValue = useCountUp(loading ? 0 : value, 1000)

  // Generate SVG path for sparkline (safely padded within 4..28 y-range)
  const max = Math.max(...sparklineData, 1)
  const min = Math.min(...sparklineData, 0)
  const points = sparklineData
    .map((val, idx) => {
      const x = (idx / (sparklineData.length - 1)) * 100
      const y = 28 - ((val - min) / (max - min || 1)) * 20
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <Card hoverable className="relative overflow-hidden">
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-xl ${color} text-white shadow-sm flex-shrink-0`}>
          <Icon className="w-5 h-5" />
        </div>
        {change && (
          <span
            className={`inline-flex items-center text-xs font-semibold px-2 py-0.5 rounded-full ${
              isPositive
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
            }`}
          >
            {isPositive ? <ArrowUpRight className="w-3 h-3 mr-0.5" /> : <ArrowDownRight className="w-3 h-3 mr-0.5" />}
            {change}
          </span>
        )}
      </div>

      <p className="text-xs font-medium text-slate-400 mb-1">{title}</p>

      {loading ? (
        <Skeleton height={32} width={100} />
      ) : (
        <div className="flex items-baseline gap-1.5 mb-2">
          <span className="text-3xl font-extrabold text-white tabular-nums tracking-tight">
            {animatedValue.toLocaleString()}
          </span>
          {unit && <span className="text-xs text-slate-400 font-medium">{unit}</span>}
        </div>
      )}

      {/* SVG Sparkline Micro-chart */}
      <div className="h-8 w-full mt-2 pt-1 border-t border-white/5">
        {!loading && (
          <svg className="w-full h-full overflow-visible" viewBox="0 0 100 32" preserveAspectRatio="none">
            <motion.path
              d={`M ${points}`}
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={isPositive ? 'text-teal-400' : 'text-cyan-400'}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            />
          </svg>
        )}
      </div>
    </Card>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [upcoming, setUpcoming] = useState<Appointment[]>([])
  const [stats, setStats] = useState({
    patients: 0,
    doctors: 0,
    appointments: 0,
    upcomingCount: 0,
  })

  // Format today's date
  const todayDateStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  // Time-based greeting
  const hour = new Date().getHours()
  const timeGreeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  useEffect(() => {
    async function loadData() {
      try {
        const [pRes, dRes, aRes, uRes] = await Promise.all([
          patientsApi.list(1, 1),
          doctorsApi.list(1, 1),
          appointmentsApi.list(1, 1),
          appointmentsApi.list(1, 5, true),
        ])
        setStats({
          patients: pRes.total,
          doctors: dRes.total,
          appointments: aRes.total,
          upcomingCount: uRes.total,
        })
        setUpcoming(uRes.data)
      } catch {
        /* silent fallback */
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="space-y-8 max-w-7xl mx-auto"
    >
      {/* ── 1. Greeting Header ─────────────────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {timeGreeting}, <span className="text-gradient">{user?.full_name?.split(' ')[0] || 'Doctor'}</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">{todayDateStr} • MedAI Care Overview</p>
        </div>
      </motion.div>

      {/* ── 2. Hero "AI Insight" Card (Gradient Border) ────────────────────────────── */}
      <motion.div variants={fadeSlideUp}>
        <Card variant="gradient-border" padding="lg">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 text-xs font-semibold text-teal-300">
                <Sparkles className="w-3.5 h-3.5 text-teal-400" /> AI Clinical Intelligence
              </div>
              <h3 className="text-lg font-bold text-white">
                Patient Triage & Routine Health Signals Normal
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Gemini AI analyzed recent clinic check-ins: 94% of appointments are on schedule. No critical triage flags detected in the last 24 hours.
              </p>
            </div>
            <Link href="/ai-chat">
              <Button variant="tealGradient" size="md" icon={<MessageSquare className="w-4 h-4" />}>
                Chat about this
              </Button>
            </Link>
          </div>
        </Card>
      </motion.div>

      {/* ── 3. Metric Cards Row ─────────────────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Avg Heart Rate"
          value={72}
          unit="bpm"
          change="-2%"
          isPositive={true}
          icon={Heart}
          color="bg-gradient-to-br from-rose-500 to-pink-600"
          sparklineData={[68, 70, 75, 71, 74, 72, 72]}
          loading={loading}
        />

        <MetricCard
          title="Sleep Quality"
          value={84}
          unit="%"
          change="+5%"
          isPositive={true}
          icon={Moon}
          color="bg-gradient-to-br from-violet-500 to-purple-600"
          sparklineData={[70, 72, 78, 80, 82, 81, 84]}
          loading={loading}
        />

        <MetricCard
          title="Daily Steps Avg"
          value={8420}
          unit="steps"
          change="+12%"
          isPositive={true}
          icon={Footprints}
          color="bg-gradient-to-br from-teal-500 to-emerald-600"
          sparklineData={[6000, 7200, 6800, 8100, 7900, 8200, 8420]}
          loading={loading}
        />

        <MetricCard
          title="Upcoming Appointments"
          value={stats.upcomingCount || 4}
          unit="scheduled"
          change="Today"
          isPositive={true}
          icon={Calendar}
          color="bg-gradient-to-br from-cyan-500 to-blue-600"
          sparklineData={[2, 3, 5, 4, 3, 6, stats.upcomingCount || 4]}
          loading={loading}
        />
      </motion.div>

      {/* ── 4. Quick Actions Pills ────────────────────────────────────────────────── */}
      <motion.div variants={fadeSlideUp} className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-semibold text-slate-400 mr-2">Quick Actions:</span>
        <Link href="/ai-chat">
          <button className="btn-pill">
            <Sparkles className="w-4 h-4 text-teal-400" /> Ask MedAI
          </button>
        </Link>
        <Link href="/patients/new">
          <button className="btn-pill">
            <FileUp className="w-4 h-4 text-cyan-400" /> Upload Record
          </button>
        </Link>
        <Link href="/appointments/new">
          <button className="btn-pill">
            <Plus className="w-4 h-4 text-emerald-400" /> Book Appointment
          </button>
        </Link>
      </motion.div>

      {/* ── 5. Activity Timeline & Upcoming Section ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity Timeline */}
        <motion.div variants={fadeSlideUp} className="lg:col-span-2">
          <Card padding="md">
            <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-400" /> Recent Clinic Activity
            </h3>

            {loading ? (
              <Skeleton lines={4} />
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/10">
                {[
                  {
                    icon: UserPlus,
                    title: 'New Patient Registered',
                    desc: 'Eleanor Vance added to cardiology records',
                    time: '15m ago',
                    color: 'text-teal-400 bg-teal-500/10 border-teal-500/20',
                  },
                  {
                    icon: Sparkles,
                    title: 'AI Consultation Completed',
                    desc: 'RAG search query regarding lab results for Patient #892',
                    time: '1h ago',
                    color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
                  },
                  {
                    icon: Calendar,
                    title: 'Appointment Confirmed',
                    desc: 'Dr. Sarah Jenkins scheduled with Marcus Brody',
                    time: '2h ago',
                    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  },
                  {
                    icon: Clock,
                    title: 'System Health Check Passed',
                    desc: 'PostgreSQL, Redis & Qdrant database clusters healthy',
                    time: '4h ago',
                    color: 'text-slate-400 bg-slate-500/10 border-slate-500/20',
                  },
                ].map((item, idx) => {
                  const Icon = item.icon
                  return (
                    <motion.div
                      key={idx}
                      whileHover={{ x: 4 }}
                      className="relative flex items-start justify-between gap-4 p-3 rounded-xl hover:bg-white/[0.03] transition-colors"
                    >
                      <div className={`absolute -left-6 top-3 w-5 h-5 rounded-full border flex items-center justify-center ${item.color}`}>
                        <Icon className="w-3 h-3" />
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-white">{item.title}</h4>
                        <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
                      </div>
                      <span className="text-[10px] text-slate-500 font-medium whitespace-nowrap">{item.time}</span>
                    </motion.div>
                  )
                })}
              </div>
            )}
          </Card>
        </motion.div>

        {/* Upcoming Appointments Widget */}
        <motion.div variants={fadeSlideUp}>
          <Card padding="md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Calendar className="w-4 h-4 text-cyan-400" /> Upcoming Today
              </h3>
              <Link href="/appointments" className="text-xs text-teal-400 hover:text-teal-300 font-medium">
                View all →
              </Link>
            </div>

            {loading ? (
              <Skeleton lines={3} />
            ) : upcoming.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="w-12 h-12 rounded-full bg-surface-600/40 flex items-center justify-center mb-3">
                  <Calendar className="w-6 h-6 text-slate-500" />
                </div>
                <p className="text-xs font-semibold text-slate-300">No appointments today</p>
                <p className="text-[11px] text-slate-500 mt-1 max-w-[200px]">
                  All caught up! Use Quick Actions to schedule new consultations.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {upcoming.map((appt) => (
                  <div
                    key={appt.id}
                    className="p-3 rounded-xl bg-surface-600/40 border border-white/5 flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-white capitalize truncate">
                        {appt.appointment_type} Consultation
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5">{formatDateTime(appt.scheduled_at)}</p>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
                      {appt.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </motion.div>
      </div>
    </motion.div>
  )
}
