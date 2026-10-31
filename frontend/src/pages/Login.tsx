import { useNavigate } from 'react-router-dom'
import { seedMockToken, AUTH_MODE } from '@/lib/auth'
import { ShieldCheck } from 'lucide-react'

export default function Login() {
  const navigate = useNavigate()

  function handleMockLogin() {
    seedMockToken()
    navigate('/')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-center gap-2">
          <ShieldCheck className="h-10 w-10 text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">ClaimSense AI</h1>
          <p className="text-sm text-gray-500">AutoSure Claims Co-Pilot</p>
        </div>

        {AUTH_MODE === 'mock' ? (
          <div className="space-y-4">
            <p className="rounded-md bg-yellow-50 border border-yellow-200 px-3 py-2 text-xs text-yellow-800">
              Local dev mode — mock auth enabled
            </p>
            <button
              onClick={handleMockLogin}
              className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              Sign in as Local Adjuster
            </button>
          </div>
        ) : (
          <p className="text-center text-sm text-gray-500">
            Cognito sign-in UI loads here in staging/prod.
          </p>
        )}
      </div>
    </div>
  )
}
