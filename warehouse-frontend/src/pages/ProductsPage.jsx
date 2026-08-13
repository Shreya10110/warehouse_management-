import { Plus } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'

const initial = { sku: '', name: '', description: '', category: '', brand: '', unit: 'EA', barcode: '' }
export default function ProductsPage() {
  const { data = [], loading, error, reload } = useApi(api.products, []); const [open, setOpen] = useState(false); const [form, setForm] = useState(initial); const [busy, setBusy] = useState(false); const [formError, setFormError] = useState('')
  const change = (e) => setForm({ ...form, [e.target.name]: e.target.value })
  async function submit(e) { e.preventDefault(); setBusy(true); setFormError(''); try { await api.createProduct(form); setOpen(false); setForm(initial); reload() } catch (err) { setFormError(err.message) } finally { setBusy(false) } }
  return <><PageHeader eyebrow="Catalog" title="Products / SKUs" description="Products must exist in the master catalog before stock can be received." action={<button onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Add product</button>} />{error && <p className="mb-4 text-red-600">{error}</p>}<DataTable rows={data ?? []} empty={loading ? 'Loading products…' : 'No products created'} columns={[{ key: 'sku', label: 'SKU' }, { key: 'name', label: 'Product' }, { key: 'category', label: 'Category' }, { key: 'brand', label: 'Brand' }, { key: 'unit', label: 'Unit' }, { key: 'is_active', label: 'Status', render: (v) => <StatusBadge value={v ? 'ACTIVE' : 'INACTIVE'} /> }]} /><Modal title="Create product" open={open} onClose={() => setOpen(false)}><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">{formError && <p className="sm:col-span-2 text-sm text-red-600">{formError}</p>}{Object.keys(initial).map((key) => <Field key={key} label={key.replaceAll('_', ' ')} name={key} value={form[key]} onChange={change} required={!['description', 'brand', 'barcode'].includes(key)} />)}<div className="sm:col-span-2 flex justify-end"><SubmitButton busy={busy}>Create product</SubmitButton></div></form></Modal></>
}
