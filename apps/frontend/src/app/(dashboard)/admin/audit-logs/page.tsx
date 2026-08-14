'use client'

import React, { useEffect, useState } from 'react'
import { ShieldCheck, Loader2 } from 'lucide-react'
import apiClient from '@/lib/api/client'

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/medai/admin/audit-logs')
      setLogs(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch audit logs', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">System Audit Trail</h1>
          <p className="text-xs text-slate-400 mt-1">Audit log of system activity, user operations, and data changes.</p>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Timestamp</th>
              <th className="p-3.5">User ID</th>
              <th className="p-3.5">Action</th>
              <th className="p-3.5">Entity Type</th>
              <th className="p-3.5">Entity ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500 font-sans">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500 font-sans">
                  No audit log entries recorded yet.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 text-slate-400">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : '-'}
                  </td>
                  <td className="p-3.5 text-teal-300">{log.user_id ? log.user_id.slice(0, 8) + '...' : 'System'}</td>
                  <td className="p-3.5 text-slate-100 font-semibold">{log.action}</td>
                  <td className="p-3.5 text-indigo-300">{log.entity_type}</td>
                  <td className="p-3.5 text-slate-500">{log.entity_id ? log.entity_id.slice(0, 8) + '...' : '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
