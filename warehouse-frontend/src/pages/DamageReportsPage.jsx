import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

export default function DamageReportsPage() {
  const { user } = useAuth(); const { data = [], loading, error, reload } = useApi(api.damageReports, [])
  async function resolve(row, resolution) { await api.resolveDamage(row.id, resolution); reload() }
  return <><PageHeader eyebrow="Quality control" title="Damage reports" description="Photo evidence, damaged quantities and final disposition history." />{error && <p className="mb-4 text-red-600">{error}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading reports…' : 'No damage reports'} columns={[{ key: 'damage_report_id', label: 'Report ID' }, { key: 'shipment_id', label: 'Shipment' }, { key: 'sku', label: 'SKU' }, { key: 'damage_quantity', label: 'Quantity' }, { key: 'damage_type', label: 'Type' }, { key: 'damage_reason', label: 'Reason' }, { key: 'resolution_status', label: 'Status', render: (v) => <StatusBadge value={v} /> }]} actions={['OWNER', 'MANAGER'].includes(user.role) ? (row) => row.resolution_status === 'OPEN' && <select onChange={(e) => e.target.value && resolve(row, e.target.value)} defaultValue="" className="rounded-lg border border-slate-300 p-2 text-xs"><option value="">Resolve…</option><option value="RETURN_TO_SUPPLIER">Return</option><option value="DISPOSE">Dispose</option><option value="MOVE_TO_GOOD_STOCK">Move to good</option><option value="KEEP_QUARANTINED">Keep quarantined</option></select> : null} /></>
}
