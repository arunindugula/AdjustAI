import { clsx } from 'clsx'

const palette: Record<string, string> = {
  Open:        'bg-blue-100 text-blue-800',
  'In Review': 'bg-yellow-100 text-yellow-800',
  Closed:      'bg-gray-100 text-gray-600',
  Approved:    'bg-green-100 text-green-800',
  Denied:      'bg-red-100 text-red-800',
}

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', palette[status] ?? 'bg-gray-100 text-gray-600')}>
      {status}
    </span>
  )
}
