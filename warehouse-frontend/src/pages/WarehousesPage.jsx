import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'

const initial = { warehouse_code: '', name: '', address_line_1: '', address_line_2: '', city: '', state: '', postal_code: '', country: 'India', contact_phone: '', contact_email: '' }

export default function WarehousesPage() {
  const navigate = useNavigate(); const { data = [], loading, error, reload } = useApi(api.warehouses, []); const [open, setOpen] = useState(false); const [form, setForm] = useState(initial); const [busy, setBusy] = useState(false); const [formError, setFormError] = useState('')
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value })
  async function submit(event) { event.preventDefault(); setBusy(true); setFormError(''); try { await api.createWarehouse(form); setOpen(false); setForm(initial); reload() } catch (requestError) { setFormError(requestError.message) } finally { setBusy(false) } }
  return <><PageHeader eyebrow="Company network" title="Warehouses" description="Create and manage fulfillment locations, addresses, contacts and status." action={<button onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Add warehouse</button>} />{error && <p className="mb-4 text-red-600">{error}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading warehouses...' : 'No warehouses created'} columns={[{ key: 'warehouse_code', label: 'Code' }, { key: 'name', label: 'Warehouse' }, { key: 'city', label: 'City' }, { key: 'state', label: 'State' }, { key: 'contact_phone', label: 'Contact' }, { key: 'is_active', label: 'Status', render: (value) => <StatusBadge value={value ? 'ACTIVE' : 'INACTIVE'} /> }]} actions={(row) => <button onClick={() => navigate(`/admin/warehouses/${row.id}`)} className="font-semibold text-blue-600">View details</button>} /><Modal open={open} onClose={() => setOpen(false)} title="Create warehouse"><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">{formError && <p className="sm:col-span-2 text-sm text-red-600">{formError}</p>}<Field label="Warehouse code" name="warehouse_code" value={form.warehouse_code} onChange={change} /><Field label="Name" name="name" value={form.name} onChange={change} /><div className="sm:col-span-2"><Field label="Address line 1" name="address_line_1" value={form.address_line_1} onChange={change} /></div><div className="sm:col-span-2"><Field label="Address line 2" name="address_line_2" value={form.address_line_2} onChange={change} required={false} /></div><Field label="City" name="city" value={form.city} onChange={change} /><Field label="State" name="state" value={form.state} onChange={change} /><Field label="Postal code" name="postal_code" value={form.postal_code} onChange={change} /><Field label="Country" name="country" value={form.country} onChange={change} /><Field label="Contact phone" name="contact_phone" value={form.contact_phone} onChange={change} /><Field label="Contact email" name="contact_email" type="email" value={form.contact_email} onChange={change} /><div className="sm:col-span-2 flex justify-end"><SubmitButton busy={busy}>Create warehouse</SubmitButton></div></form></Modal></>
}
