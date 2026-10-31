import { useNavigate } from 'react-router-dom'
import { StatusPill } from './StatusPill'
import type { Claim } from '@/lib/api'

export function ClaimsTable({ claims }: { claims: Claim[] }) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {['Claim ID', 'Vehicle', 'Incident Type', 'Incident Date', 'Repair Est.', 'Status', ''].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {claims.map((c) => (
            <tr
              key={c.claim_id}
              className="cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => navigate(`/claims/${c.claim_id}`)}
            >
              <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.claim_id}</td>
              <td className="px-4 py-3 font-medium">{c.vehicle_year} {c.vehicle_make} {c.vehicle_model}</td>
              <td className="px-4 py-3 text-gray-600">{c.incident_type}</td>
              <td className="px-4 py-3 text-gray-600">{c.incident_date}</td>
              <td className="px-4 py-3 font-medium">
                ${Number(c.repair_estimate_usd).toLocaleString()}
              </td>
              <td className="px-4 py-3">
                <StatusPill status={c.claim_status} />
              </td>
              <td className="px-4 py-3 text-right text-blue-600 text-xs">Review →</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
