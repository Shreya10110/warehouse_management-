import { Building2, Plus } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'

const blank = { seller_code: '', name: '', contact_name: '', email: '', phone: '', address: '' }

export default function SellersPage() {
  const { data = [], loading, error, reload } = useApi(api.sellers, [])
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(blank)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  async function submit(event) {
    event.preventDefault(); setBusy(true); setFormError('')
    try { await api.createSeller(Object.fromEntries(Object.entries(form).map(([key, value]) => [key, value || null]))); setOpen(false); setForm(blank); reload() }
    catch (requestError) { setFormError(requestError.message) } finally { setBusy(false) }
  }
  return <><PageHeader eyebrow="Master data" title="Sellers and suppliers" description="Admin-approved sellers used by expected inbound shipments and outbound orders." action={<button onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Add seller</button>} />{error && <p className="mb-4 text-red-600">{error}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading sellers...' : 'No sellers created'} columns={[{ key: 'seller_code', label: 'Code' }, { key: 'name', label: 'Seller' }, { key: 'contact_name', label: 'Contact' }, { key: 'email', label: 'Email' }, { key: 'phone', label: 'Phone' }, { key: 'is_active', label: 'Status', render: (value) => <StatusBadge value={value ? 'ACTIVE' : 'INACTIVE'} /> }]} /><Modal title="Create seller" open={open} onClose={() => setOpen(false)}><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">{formError && <p className="sm:col-span-2 text-red-600">{formError}</p>}{Object.keys(blank).map((key) => <Field key={key} label={key.replaceAll('_', ' ')} name={key} type={key === 'email' ? 'email' : 'text'} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} required={['seller_code', 'name'].includes(key)} />)}<div className="sm:col-span-2 flex justify-end"><SubmitButton busy={busy}><span className="flex items-center gap-2"><Building2 className="h-4 w-4" /> Create seller</span></SubmitButton></div></form></Modal></>
}
