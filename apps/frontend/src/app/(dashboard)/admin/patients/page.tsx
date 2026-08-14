'use client'

import React, { useEffect, useState } from 'react'
import { Search, Loader2, Trash2 } from 'lucide-react'
import apiClient from '@/lib/api/client'

export default function AdminPatientsPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const fetchPatients = async () => {
    try {
      setLoading(true)
      const res = await apiClient.get('/medai/patients')
      setPatients(res.data?.data || [])
    } catch (err) {
      console.error('Failed to fetch patients', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPatients()
  }, [])

  const handleDelete = async (id: string) => {
    if (!confirm('Soft-delete this patient record?')) return
    try {
      await apiClient.delete(`/medai/patients/${id}`)
      fetchPatients()
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`)
    }
  }

  const filtered = patients.filter(
    (p) =>
      p.full_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.email?.toLowerCase().includes(search.toLowerCase()) ||
      p.phone?.includes(search)
  )

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Patient Directory</h1>
          <p className="text-xs text-slate-400 mt-1">Full CRUD patient registry with soft-delete controls.</p>
        </div>
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
        <input
          type="text"
          placeholder="Search by patient name, email, or phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/50"
        />
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950 text-slate-400 font-medium uppercase text-[10px] tracking-wider border-b border-slate-800">
            <tr>
              <th className="p-3.5">Patient Name</th>
              <th className="p-3.5">Contact Email</th>
              <th className="p-3.5">Phone Number</th>
              <th className="p-3.5">Blood Group</th>
              <th className="p-3.5">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-teal-400" />
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No patient records found.
                </td>
              </tr>
            ) : (
              filtered.map((patient) => (
                <tr key={patient.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3.5 font-semibold text-slate-100">{patient.full_name}</td>
                  <td className="p-3.5 text-slate-400">{patient.email || '-'}</td>
                  <td className="p-3.5 font-mono">{patient.phone}</td>
                  <td className="p-3.5 font-mono text-teal-300">{patient.blood_group || 'Unspecified'}</td>
                  <td className="p-3.5">
                    <button
                      onClick={() => handleDelete(patient.id)}
                      className="p-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition-colors"
                      title="Soft-delete patient"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
