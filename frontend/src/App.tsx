import { BrowserRouter, Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom'
import { ShieldCheck, LayoutDashboard, ScrollText, LogOut } from 'lucide-react'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import ClaimDetail from '@/pages/ClaimDetail'
import AuditLog from '@/pages/AuditLog'
import { clearAuth } from '@/lib/auth'

function isAuthenticated() {
  return !!localStorage.getItem('id_token')
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return isAuthenticated() ? <>{children}</> : <Navigate to="/login" replace />
}

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()

  function logout() {
    clearAuth()
    navigate('/login')
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
    }`

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="flex items-center gap-2 px-4 py-5 border-b border-gray-100">
          <ShieldCheck className="h-6 w-6 text-blue-600" />
          <div>
            <p className="text-sm font-bold text-gray-900">ClaimSense AI</p>
            <p className="text-xs text-gray-400">AutoSure</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          <NavLink to="/" end className={navLinkClass}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>
          <NavLink to="/audit" className={navLinkClass}>
            <ScrollText className="h-4 w-4" />
            Audit Log
          </NavLink>
        </nav>

        <div className="p-3 border-t border-gray-100">
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Shell>
                <Dashboard />
              </Shell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/claims/:claimId"
          element={
            <ProtectedRoute>
              <Shell>
                <ClaimDetail />
              </Shell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <ProtectedRoute>
              <Shell>
                <AuditLog />
              </Shell>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
