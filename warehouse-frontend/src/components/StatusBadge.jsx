const tones = {
  ACTIVE: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', COMPLETED: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', SHIPPED: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20', MATCHED: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  PENDING: 'bg-amber-50 text-amber-700 ring-amber-600/20', RECEIVING: 'bg-amber-50 text-amber-700 ring-amber-600/20', PICKING: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  DAMAGED: 'bg-red-50 text-red-700 ring-red-600/20', REJECTED: 'bg-red-50 text-red-700 ring-red-600/20', CANCELLED: 'bg-red-50 text-red-700 ring-red-600/20',
}

export default function StatusBadge({ value }) {
  const label = String(value ?? '—').replaceAll('_', ' ')
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tones[value] ?? 'bg-blue-50 text-blue-700 ring-blue-600/20'}`}>{label}</span>
}
