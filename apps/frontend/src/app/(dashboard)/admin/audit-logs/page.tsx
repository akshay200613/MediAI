'use client'

import React, { useEffect, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ShieldCheck,
  Loader2,
  Search,
  RefreshCw,
  Filter,
  User,
  Activity,
  Calendar,
  ShieldAlert,
  Info,
  X,
  Clock,
  Globe,
  Database,
  CheckCircle,
} from 'lucide-react'
import apiClient from '@/lib/api/client'
import { easeOutExpo } from '@/lib/motion'

interface AuditLogItem {
  id: string
  user_id: string | null
  user_name: string
  user_role: string
  action: string
  resource_type: string
  entity_type: string
  resource_id: string | null
  entity_id: string | null
  details: string | null
  ip_address: string
  created_at: string | null
}

interface AuditMetrics {
  total: number
  auth: number
  appointments: number
  admin: number
}

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [metrics, setMetrics] = useState<AuditMetrics>({ total: 0, auth: 0, appointments: 0, admin: 0 })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [actionFilter, setActionFilter] = useState('ALL')
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null)

  const fetchLogs = async (isManual = false) => {
    try {
      setError(null)
      if (isManual) setRefreshing(true)
      else setLoading(true)

      const params: any = { limit: 100 }
      if (actionFilter !== 'ALL') params.action = actionFilter
      if (searchQuery.trim()) params.search = searchQuery.trim()

      const res = await apiClient.get('/medai/admin/audit-logs', { params })
      const resData = res.data?.data

      if (Array.isArray(resData)) {
        setLogs(resData)
      } else if (resData && Array.isArray(resData.logs)) {
        setLogs(resData.logs)
        if (resData.metrics) {
          setMetrics(resData.metrics)
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch audit logs', err)
      setError(err.message || 'Network Error: Unable to reach backend API server at localhost:8000')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [actionFilter])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    fetchLogs(true)
  }

  // Action badge styling helper
  const getActionBadge = (action: string) => {
    switch (action) {
      case 'USER_LOGIN':
      case 'USER_REGISTER':
        return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
      case 'APPOINTMENT_BOOKED':
      case 'CONSULTATION_SAVED':
        return 'bg-teal-500/10 border-teal-500/30 text-teal-300'
      case 'DOCTOR_APPROVED':
      case 'PROFILE_UPDATED':
        return 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
      case 'APPOINTMENT_CANCELLED':
      case 'DOCTOR_DELETED':
      case 'DOCTOR_REJECTED':
        return 'bg-rose-500/10 border-rose-500/30 text-rose-400'
      default:
        return 'bg-slate-800 border-slate-700 text-slate-300'
    }
  }

  // Role badge styling helper
  const getRoleBadge = (role: string) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return 'bg-purple-500/20 text-purple-300 border-purple-500/30'
      case 'doctor':
        return 'bg-teal-500/20 text-teal-300 border-teal-500/30'
      case 'patient':
      case 'user':
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30'
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700'
    }
  }

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* ── Header Title & Actions ────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 shadow-md shadow-teal-950/40">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">System Audit Trail</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time security log of authentication events, appointments, clinical notes, and admin operations.
          </p>
        </div>

        <button
          onClick={() => fetchLogs(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-medium transition-colors shrink-0 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-teal-400 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing...' : 'Refresh Audit Log'}
        </button>
      </div>

      {/* ── Summary Metrics Cards ─────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex items-center justify-between"
        >
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Total Recorded Logs</p>
            <h3 className="text-2xl font-bold text-slate-100 mt-1">{metrics.total || logs.length}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <Activity className="w-5 h-5" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex items-center justify-between"
        >
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Auth Events</p>
            <h3 className="text-2xl font-bold text-emerald-400 mt-1">{metrics.auth}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <User className="w-5 h-5" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex items-center justify-between"
        >
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Appointments & Rx</p>
            <h3 className="text-2xl font-bold text-teal-400 mt-1">{metrics.appointments}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <Calendar className="w-5 h-5" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="p-4 rounded-2xl bg-slate-900/70 border border-slate-800 flex items-center justify-between"
        >
          <div>
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Admin Operations</p>
            <h3 className="text-2xl font-bold text-purple-400 mt-1">{metrics.admin}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </motion.div>
      </div>

      {/* ── Network Error Alert Banner ──────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between gap-4 text-xs text-rose-300">
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
            <div>
              <p className="font-semibold text-rose-200">API Connection Issue</p>
              <p className="text-[11px] text-rose-300/80 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            onClick={() => fetchLogs(true)}
            className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs transition-colors shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* ── Search & Filter Controls ─────────────────────────────────────── */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search audit logs by user, action, ID, or details payload..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
          />
        </form>

        <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
          <Filter className="w-4 h-4 text-slate-500 shrink-0" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-teal-500/50 cursor-pointer"
          >
            <option value="ALL">All Event Actions</option>
            <option value="USER_LOGIN">USER_LOGIN</option>
            <option value="USER_REGISTER">USER_REGISTER</option>
            <option value="APPOINTMENT_BOOKED">APPOINTMENT_BOOKED</option>
            <option value="APPOINTMENT_CANCELLED">APPOINTMENT_CANCELLED</option>
            <option value="CONSULTATION_SAVED">CONSULTATION_SAVED</option>
            <option value="DOCTOR_APPROVED">DOCTOR_APPROVED</option>
            <option value="DOCTOR_DELETED">DOCTOR_DELETED</option>
            <option value="PROFILE_UPDATED">PROFILE_UPDATED</option>
          </select>
        </div>
      </div>

      {/* ── Audit Logs Table ──────────────────────────────────────────────── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="p-3.5">Timestamp</th>
                <th className="p-3.5">User Identity</th>
                <th className="p-3.5">Action Code</th>
                <th className="p-3.5">Entity Target</th>
                <th className="p-3.5">Origin IP</th>
                <th className="p-3.5 text-right">Details Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans text-xs">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-teal-400 mb-2" />
                    Loading audit trail entries...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No audit log entries found matching criteria.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3.5 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-200">{log.user_name || 'System'}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${getRoleBadge(log.user_role)}`}>
                          {log.user_role || 'system'}
                        </span>
                      </div>
                      {log.user_id && (
                        <div className="text-[10px] font-mono text-slate-500 truncate max-w-[120px]">
                          ID: {log.user_id.slice(0, 8)}...
                        </div>
                      )}
                    </td>
                    <td className="p-3.5">
                      <span className={`px-2.5 py-1 rounded-lg border font-mono text-[11px] font-semibold ${getActionBadge(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3.5 font-mono text-[11px]">
                      <span className="text-indigo-300 font-semibold">{log.resource_type || log.entity_type}</span>
                      {log.resource_id && (
                        <span className="text-slate-500 block text-[10px]">
                          ID: {log.resource_id.slice(0, 8)}...
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 font-mono text-[11px] text-slate-400">
                      {log.ip_address || '127.0.0.1'}
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-teal-300 border border-slate-700/60 text-[11px] font-medium transition-colors"
                      >
                        Inspect Payload
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Log Details Inspection Modal ──────────────────────────────────── */}
      <AnimatePresence>
        {selectedLog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ ...easeOutExpo, duration: 0.2 }}
              className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4 font-sans"
            >
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Info className="w-5 h-5 text-teal-400" />
                  <h3 className="font-semibold text-sm text-slate-100">Audit Log Details</h3>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-2 text-xs text-slate-300 bg-slate-950 p-3.5 rounded-xl border border-slate-800 font-mono">
                <div className="flex justify-between py-1 border-b border-slate-800/60">
                  <span className="text-slate-500">Log ID:</span>
                  <span className="text-slate-200">{selectedLog.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/60">
                  <span className="text-slate-500">Action:</span>
                  <span className="text-teal-400 font-semibold">{selectedLog.action}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/60">
                  <span className="text-slate-500">User:</span>
                  <span className="text-slate-200">{selectedLog.user_name} ({selectedLog.user_role})</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/60">
                  <span className="text-slate-500">Resource Target:</span>
                  <span className="text-indigo-300">{selectedLog.resource_type} ({selectedLog.resource_id || '-'})</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800/60">
                  <span className="text-slate-500">Origin IP:</span>
                  <span className="text-slate-300">{selectedLog.ip_address}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Timestamp:</span>
                  <span className="text-slate-400">{selectedLog.created_at ? new Date(selectedLog.created_at).toLocaleString() : '-'}</span>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                  Payload Metadata Details
                </label>
                <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-teal-300 overflow-x-auto max-h-48 whitespace-pre-wrap">
                  {selectedLog.details
                    ? (() => {
                        try {
                          return JSON.stringify(JSON.parse(selectedLog.details), null, 2)
                        } catch {
                          return selectedLog.details
                        }
                      })()
                    : 'No additional details payload.'}
                </pre>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                >
                  Close Inspector
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

