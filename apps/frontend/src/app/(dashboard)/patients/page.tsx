'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Search, Plus, ChevronLeft, ChevronRight, User, Phone, Mail, Trash2 } from 'lucide-react'
import { patientsApi } from '@/lib/api/patients'
import { getInitials, formatDate } from '@/lib/utils'
import type { Patient } from '@/types'
import toast from 'react-hot-toast'

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const pageSize = 10

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await patientsApi.list(page, pageSize, search || undefined)
      setPatients(res.data)
      setTotal(res.total)
    } catch { toast.error('Failed to load patients') }
    finally { setLoading(false) }
  }, [page, search])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete ${name}?`)) return
    try {
      await patientsApi.delete(id)
      toast.success('Patient deleted')
      load()
    } catch { toast.error('Failed to delete') }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="text-2xl font-bold text-white">Patients</h1>
          <p className="text-slate-400 mt-1">{total} total patients registered</p>
        </div>
        <Link href="/patients/new" className="btn-primary">
          <Plus className="w-4 h-4" /> New Patient
        </Link>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search patients..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="input-field pl-10"
        />
      </div>

      {/* Table */}
      <div className="glass-card overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => <div key={i} className="shimmer h-14 rounded-xl" />)}
          </div>
        ) : patients.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500">
            <User className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-base font-medium">No patients found</p>
            <p className="text-sm mt-1">Register your first patient to get started</p>
            <Link href="/patients/new" className="btn-primary mt-4"><Plus className="w-4 h-4" /> Add Patient</Link>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Contact</th>
                <th>Gender</th>
                <th>Blood Group</th>
                <th>Registered</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map(p => (
                <tr key={p.id} onClick={() => window.location.href = `/patients/${p.id}`}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center justify-center w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 text-xs font-bold text-white flex-shrink-0">
                        {getInitials(p.full_name)}
                      </div>
                      <div>
                        <p className="font-medium text-white">{p.full_name}</p>
                        <p className="text-xs text-slate-500">{p.city || 'N/A'}</p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-1.5 text-slate-300"><Phone className="w-3 h-3 text-slate-500" />{p.phone}</div>
                      {p.email && <div className="flex items-center gap-1.5 text-slate-400 text-xs"><Mail className="w-3 h-3" />{p.email}</div>}
                    </div>
                  </td>
                  <td><span className="capitalize text-slate-300">{p.gender || '—'}</span></td>
                  <td>
                    {p.blood_group
                      ? <span className="badge-red">{p.blood_group}</span>
                      : <span className="text-slate-500">—</span>
                    }
                  </td>
                  <td className="text-slate-400 text-sm">{formatDate(p.created_at)}</td>
                  <td onClick={e => e.stopPropagation()}>
                    <button onClick={() => handleDelete(p.id, p.full_name)} className="btn-danger py-1.5 px-3 text-xs">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-white/5">
            <p className="text-sm text-slate-400">Showing {((page-1)*pageSize)+1}–{Math.min(page*pageSize, total)} of {total}</p>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(p => p-1)} disabled={page === 1} className="btn-secondary py-2 px-3 disabled:opacity-40">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-slate-300">{page} / {totalPages}</span>
              <button onClick={() => setPage(p => p+1)} disabled={page === totalPages} className="btn-secondary py-2 px-3 disabled:opacity-40">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
