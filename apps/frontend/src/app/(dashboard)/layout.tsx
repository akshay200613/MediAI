'use client'
import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Calendar,
  Settings,
  LogOut,
  Menu,
  X,
  Activity,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  ShieldCheck,
  ChevronDown,
  Users,
  Stethoscope,
} from 'lucide-react'
import { useAuth } from '@/lib/auth/context'
import { Avatar } from '@/components/ui'
import { cn } from '@/lib/utils'
import { dropdownVariants } from '@/lib/motion'
import toast from 'react-hot-toast'

interface NavItem {
  href: string
  label: string
  icon: typeof LayoutDashboard
  subItems?: { href: string; label: string; icon: typeof Users }[]
}

const getRoleNavItems = (role?: string): NavItem[] => {
  if (role === 'admin' || role === 'super_admin') {
    return [
      { href: '/admin', label: 'Admin Dashboard', icon: LayoutDashboard },
      { href: '/admin/doctors', label: 'Manage Doctors', icon: Stethoscope },
      { href: '/admin/patients', label: 'Manage Patients', icon: Users },
      { href: '/admin/appointments', label: 'Master Appointments', icon: Calendar },
      { href: '/admin/audit-logs', label: 'Audit Trail', icon: ShieldCheck },
      { href: '/settings', label: 'Account Settings', icon: Settings },
    ]
  }
  if (role === 'doctor') {
    return [
      { href: '/doctor', label: 'Doctor Console', icon: LayoutDashboard },
      { href: '/doctor/appointments', label: 'Patient Roster & Notes', icon: Calendar },
      { href: '/settings', label: 'Account & Schedule Settings', icon: Settings },
      { href: '/ai-chat', label: 'Clinical AI RAG', icon: MessageSquare },
    ]
  }
  if (role === 'patient' || role === 'user') {
    return [
      { href: '/patient', label: 'Patient Portal', icon: LayoutDashboard },
      { href: '/patient/book', label: 'Book Appointment', icon: Calendar },
      { href: '/patient/appointments', label: 'My Appointments', icon: Calendar },
      { href: '/patient/profile', label: 'Medical Profile', icon: FileText },
      { href: '/patient/chat', label: 'AI Medical Chat', icon: MessageSquare },
    ]
  }

  // Fallback platform nav
  return [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/ai-chat', label: 'AI Chat', icon: MessageSquare },
    { href: '/appointments', label: 'Appointments', icon: Calendar },
  ]
}


export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [recordsOpen, setRecordsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [hasNotification, setHasNotification] = useState(true)

  const isFullHeightPage = pathname === '/ai-chat'

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login')
        return
      }

      const role = user?.role
      const isVerified = user?.is_verified !== false

      if (pathname.startsWith('/admin') && role !== 'admin' && role !== 'super_admin') {
        router.replace('/unauthorized')
      } else if (pathname.startsWith('/doctor')) {
        if (role !== 'doctor' && role !== 'admin' && role !== 'super_admin') {
          if (!isVerified) {
            router.replace('/pending-approval')
          } else {
            router.replace('/unauthorized')
          }
        }
      } else if (
        pathname.startsWith('/patient') &&
        role !== 'patient' &&
        role !== 'user' &&
        role !== 'admin' &&
        role !== 'doctor'
      ) {
        router.replace('/unauthorized')
      }
    }
  }, [isAuthenticated, isLoading, user, pathname, router])

  useEffect(() => {
    const stored = localStorage.getItem('sidebar_collapsed')
    if (stored !== null) setCollapsed(stored === 'true')
  }, [])

  const toggleCollapsed = () => {
    const next = !collapsed
    setCollapsed(next)
    localStorage.setItem('sidebar_collapsed', String(next))
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-900">
        <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return null

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ── Left Sidebar (72px collapsed / 240px expanded) ───────────────────────── */}
      <aside
        className={cn(
          'glass-sidebar fixed lg:relative z-40 h-full flex flex-col transition-all duration-300 ease-in-out',
          collapsed ? 'w-[72px]' : 'w-[240px]',
          mobileOpen ? 'translate-x-0 w-[240px]' : '-translate-x-full lg:translate-x-0',
        )}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-white/5">
          <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-glow flex-shrink-0">
              <Activity className="w-5 h-5 text-white" />
            </div>
            {(!collapsed || mobileOpen) && (
              <div className="flex flex-col min-w-0">
                <span className="text-base font-extrabold text-white tracking-wide leading-tight">MedAI</span>
                <span className="text-[10px] text-slate-400 font-medium">Clinic Management OS</span>
              </div>
            )}
          </Link>
          <button
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setMobileOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto overflow-x-hidden">
          {(!collapsed || mobileOpen) && (
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
              Main Menu
            </p>
          )}

          {getRoleNavItems(user?.role).map((item) => {
            const Icon = item.icon
            const isSubActive = item.subItems?.some((sub) => pathname.startsWith(sub.href))
            const isActive =
              (item.href === '/dashboard' ? pathname === '/dashboard' : pathname.startsWith(item.href)) ||
              isSubActive

            if (item.subItems) {
              return (
                <div key={item.href}>
                  <button
                    onClick={() => {
                      if (collapsed) setCollapsed(false)
                      setRecordsOpen(!recordsOpen)
                    }}
                    className={cn(
                      'nav-item w-full justify-between group',
                      isActive ? 'active' : '',
                    )}
                    title={collapsed ? item.label : undefined}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5 flex-shrink-0" />
                      {(!collapsed || mobileOpen) && <span className="truncate">{item.label}</span>}
                    </div>
                    {(!collapsed || mobileOpen) && (
                      <ChevronDown
                        className={cn(
                          'w-4 h-4 text-slate-400 transition-transform duration-200',
                          recordsOpen ? 'rotate-180' : '',
                        )}
                      />
                    )}
                  </button>

                  {/* Submenu */}
                  <AnimatePresence>
                    {(recordsOpen || isSubActive) && (!collapsed || mobileOpen) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="pl-9 pr-2 py-1 space-y-1 overflow-hidden"
                      >
                        {item.subItems.map((sub) => {
                          const SubIcon = sub.icon
                          const isSubItemActive = pathname.startsWith(sub.href)
                          return (
                            <Link
                              key={sub.href}
                              href={sub.href}
                              onClick={() => setMobileOpen(false)}
                              className={cn(
                                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                                isSubItemActive
                                  ? 'text-teal-400 bg-teal-500/10'
                                  : 'text-slate-400 hover:text-white hover:bg-white/5',
                              )}
                            >
                              <SubIcon className="w-3.5 h-3.5" />
                              {sub.label}
                            </Link>
                          )
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn('nav-item group', isActive ? 'active' : '')}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {(!collapsed || mobileOpen) && <span className="truncate">{item.label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-white/5 space-y-3">
          {(!collapsed || mobileOpen) && (
            <div className="trust-badge px-2">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              <span className="truncate">Encrypted & HIPAA-conscious</span>
            </div>
          )}

          <button
            onClick={toggleCollapsed}
            className="hidden lg:flex items-center justify-center w-full py-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors focus-ring"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* ── Main Layout Column ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 flex items-center justify-between px-4 lg:px-6 border-b border-white/5 bg-surface-800/50 backdrop-blur-md flex-shrink-0 z-20">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Global Search Bar */}
            <div className="relative w-44 sm:w-64 md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search patients, records..."
                className="w-full bg-surface-600/40 border border-white/10 rounded-full pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-teal-500/60 focus:ring-1 focus:ring-teal-500/30 transition-all"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') toast('Search feature active', { icon: '🔍' })
                }}
              />
              <span className="hidden sm:inline-block absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-slate-500 border border-white/10 rounded px-1">
                ⌘K
              </span>
            </div>
          </div>

          {/* Right: Notifications & Profile Menu */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setHasNotification(false)
                toast('No urgent notifications', { icon: '🔔' })
              }}
              className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors focus-ring"
              title="Notifications"
            >
              <Bell className={cn('w-5 h-5', hasNotification && 'animate-bell-shake')} />
              {hasNotification && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal-400 ring-2 ring-surface-800" />
              )}
            </button>

            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2.5 p-1 rounded-full hover:bg-white/5 transition-colors focus-ring"
              >
                <Avatar name={user?.full_name || user?.email || 'User'} size="sm" />
                <span className="hidden md:inline-block text-xs font-semibold text-slate-200 max-w-[120px] truncate">
                  {user?.full_name || user?.email}
                </span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden md:block" />
              </button>

              <AnimatePresence>
                {profileOpen && (
                  <motion.div
                    variants={dropdownVariants}
                    initial="hidden"
                    animate="show"
                    exit="exit"
                    className="absolute right-0 mt-2 w-48 rounded-2xl glass-card border border-white/10 p-2 shadow-xl z-50"
                  >
                    <div className="px-3 py-2 border-b border-white/5 mb-1">
                      <p className="text-xs font-semibold text-white truncate">{user?.full_name}</p>
                      <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
                    </div>
                    <Link
                      href={(user?.role === 'patient' || user?.role === 'user') ? '/patient/profile' : '/settings'}
                      onClick={() => setProfileOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-slate-300 hover:text-white hover:bg-white/5 transition-colors"
                    >
                      <Settings className="w-4 h-4" /> {(user?.role === 'patient' || user?.role === 'user') ? 'Medical Profile' : 'Account Settings'}
                    </Link>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        logout()
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <LogOut className="w-4 h-4" /> Log out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page Content Viewport */}
        <main className={cn('flex-1 min-h-0', isFullHeightPage ? 'p-0 overflow-hidden' : 'overflow-y-auto p-4 sm:p-6 lg:p-8')}>
          {children}
        </main>
      </div>
    </div>
  )
}
