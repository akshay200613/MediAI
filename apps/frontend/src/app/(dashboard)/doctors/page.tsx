'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Search, Plus, Stethoscope, Phone, Star, ChevronLeft, ChevronRight, Trash2, CheckCircle, XCircle } from 'lucide-react'
import { doctorsApi } from '@/lib/api/doctors'
import { getInitials } from '@/lib/utils'
import type { Doctor } from '@/types'
import toast from 'react-hot-toast'

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const pageSize = 12

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await doctorsApi.list(page, pageSize, search || undefined)
      setDoctors(res.data)
      setTotal(res.total)
    } catch { toast.error('Failed to load doctors') }
    finally { setLoading(false) }
  }, [page, search])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Remove Dr. ${name}?`)) return
    try { await doctorsApi.delete(id); toast.success('Doctor removed'); load() }
    catch { toast.error('Failed to delete') }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="page-header">
        <div>
          <h1 className="text-2xl font-bold text-white">Doctors</h1>
          <p className="text-slate-400 mt-1">{total} doctors registered</p>
        </div>
        <Link href="/doctors/new" className="btn-primary"><Plus className="w-4 h-4" /> Add Doctor</Link>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input type="text" placeholder="Search by name or specialty..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }} className="input-field pl-10" />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="shimmer h-48 rounded-2xl" />)}
        </div>
      ) : doctors.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500 glass-card">
          <Stethoscope className="w-12 h-12 mb-3 opacity-30" />
          <p className="text-base font-medium">No doctors found</p>
          <Link href="/doctors/new" className="btn-primary mt-4"><Plus className="w-4 h-4" /> Add Doctor</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {doctors.map(d => (
            <Link key={d.id} href={`/doctors/${d.id}`}>
              <div className="glass-card p-5 hover:border-primary-500/20 hover:shadow-glow hover:scale-[1.01] transition-all duration-200 cursor-pointer group">
                <div className="flex items-start gap-4">
                  {d.profile_image_url ? (
                    <div className="w-12 h-12 rounded-xl flex-shrink-0 overflow-hidden relative border border-white/10">
                      <img src={d.profile_image_url.startsWith('http') ? d.profile_image_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${d.profile_image_url}`} alt={d.full_name} className="object-cover w-full h-full" />
                    </div>
                  ) : (
                    <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-accent-500 to-primary-500 text-sm font-bold text-white flex-shrink-0">
                      {getInitials(d.full_name)}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-white truncate">{d.full_name}</p>
                    <p className="text-accent-400 text-sm">{d.specialty}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                      <span className="text-xs text-slate-400">{d.years_of_experience} yrs exp.</span>
                    </div>
                  </div>
                  <button onClick={e => { e.preventDefault(); handleDelete(d.id, d.full_name) }}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
                  <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                    <Phone className="w-3 h-3" />{d.phone}
                  </div>
                  <div className={`flex items-center gap-1 text-xs font-medium ${d.is_available ? 'text-emerald-400' : 'text-slate-500'}`}>
                    {d.is_available ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                    {d.is_available ? 'Available' : 'Unavailable'}
                  </div>
                </div>
                {d.consultation_fee > 0 && (
                  <p className="mt-2 text-xs text-slate-500">Consultation: <span className="text-slate-300 font-medium">${d.consultation_fee}</span></p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}

      {Math.ceil(total / pageSize) > 1 && (
        <div className="flex items-center justify-center gap-4">
          <button onClick={() => setPage(p => p-1)} disabled={page === 1} className="btn-secondary py-2 px-3 disabled:opacity-40">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-slate-400">{page} of {Math.ceil(total / pageSize)}</span>
          <button onClick={() => setPage(p => p+1)} disabled={page >= Math.ceil(total/pageSize)} className="btn-secondary py-2 px-3 disabled:opacity-40">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}
