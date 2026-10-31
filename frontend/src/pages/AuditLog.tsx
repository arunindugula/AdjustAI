export default function AuditLog() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-sm text-gray-500">Decision history across all claims</p>
      </div>
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center">
        <p className="text-sm text-gray-400">Audit log view — coming in Step 6</p>
        <p className="text-xs text-gray-300 mt-1">Will query DecisionsTable GSI (claim_id-index)</p>
      </div>
    </div>
  )
}
