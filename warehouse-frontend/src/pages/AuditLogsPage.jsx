import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'

export default function AuditLogsPage() {
  const { data = [], loading, error } = useApi(api.auditLogs, [])
  return <><PageHeader eyebrow="Accountability" title="Audit logs" description="Immutable history of users, actions, entities and warehouse context." />{error && <p className="mb-4 text-red-600">{error}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading audit history…' : 'No audit events'} columns={[{ key: 'created_at', label: 'Date & Time', render: (v) => new Date(v).toLocaleString() }, { key: 'entity_type', label: 'Module' }, { key: 'action', label: 'Action', render: (v) => <StatusBadge value={v} /> }, { key: 'entity_id', label: 'Reference ID' }, { key: 'warehouse_id', label: 'Warehouse' }, { key: 'user_role', label: 'Role' }, { key: 'user_id', label: 'User' }]} /></>
}
