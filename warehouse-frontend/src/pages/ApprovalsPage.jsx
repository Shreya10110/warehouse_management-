import { ShieldCheck, UserCheck, UserX } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

export default function ApprovalsPage() {
  const { user } = useAuth(); const { data = [], loading, error, reload } = useApi(api.pendingApprovals, []); const { data: warehouses = [] } = useApi(api.warehouses, []); const [actionError, setActionError] = useState(''); const [busyId, setBusyId] = useState('')
  async function approve(row) { setBusyId(row.id); setActionError(''); try { await api.approveRegistration(row.id); reload() } catch (requestError) { setActionError(requestError.message) } finally { setBusyId('') } }
  async function reject(row) { const reason = window.prompt('Reason for rejection:'); if (!reason) return; setBusyId(row.id); setActionError(''); try { await api.rejectRegistration(row.id, reason); reload() } catch (requestError) { setActionError(requestError.message) } finally { setBusyId('') } }
  return <><PageHeader eyebrow="Credential verification" title={user.role === 'OWNER' ? 'Manager approval queue' : 'Employee approval queue'} description={user.role === 'OWNER' ? 'Verify managers before they receive access to a warehouse.' : 'Verify inbound and outbound employees for your assigned warehouse only.'} action={<div className="rounded-xl bg-blue-50 p-3 text-blue-700"><ShieldCheck /></div>} />{(error || actionError) && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error || actionError}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading approval requests...' : 'No pending verification requests'} columns={[{ key: 'first_name', label: 'Applicant', render: (_, row) => `${row.first_name} ${row.last_name}` }, { key: 'email', label: 'Email' }, { key: 'mobile', label: 'Phone' }, { key: 'role', label: 'Requested Role', render: (value) => <StatusBadge value={value} /> }, { key: 'warehouse_id', label: 'Warehouse', render: (value) => warehouses.find((warehouse) => warehouse.id === value)?.name ?? value }, { key: 'created_at', label: 'Requested', render: (value) => new Date(value).toLocaleString() }]} actions={(row) => <div className="flex gap-2"><button disabled={busyId === row.id} onClick={() => approve(row)} className="flex items-center gap-1 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"><UserCheck className="h-4 w-4" /> Approve</button><button disabled={busyId === row.id} onClick={() => reject(row)} className="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-100 disabled:opacity-50"><UserX className="h-4 w-4" /> Reject</button></div>} /></>
}
