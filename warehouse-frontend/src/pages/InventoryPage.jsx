import { SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, Select, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

export default function InventoryPage({ filter = '' }) {
  const { user } = useAuth()
  const { data, loading, error, reload } = useApi(() => api.inventory(filter), [filter])
  const { data: warehouseData } = useApi(api.warehouses, [])
  const inventory = Array.isArray(data) ? data : []
  const warehouses = Array.isArray(warehouseData) ? warehouseData : []
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ sku: '', quantity_change: '', reason: '', warehouse_id: '' })
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const change = (event) => setForm({ ...form, [event.target.name]: event.target.value })

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setFormError('')
    try {
      await api.adjustInventory({ ...form, quantity_change: Number(form.quantity_change), warehouse_id: form.warehouse_id || null })
      setOpen(false)
      reload()
    } catch (requestError) {
      setFormError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { key: 'sku', label: 'SKU' },
    { key: 'warehouse_id', label: 'Warehouse', render: (value) => warehouses.find((item) => item.id === value)?.warehouse_code ?? value?.slice(-6) ?? '—' },
    { key: 'on_hand_quantity', label: 'On Hand' },
    { key: 'reserved_quantity', label: 'Reserved' },
    { key: 'damaged_quantity', label: 'Damaged' },
    { key: 'quarantine_quantity', label: 'Quarantine' },
    { key: 'available_quantity', label: 'Available', render: (value) => <StatusBadge value={String(value)} /> },
    { key: 'updated_at', label: 'Last Updated', render: (value) => value ? new Date(value).toLocaleString() : '—' },
  ]

  return <>
    <PageHeader eyebrow="Stock control" title={filter.includes('quarantine') ? 'Quarantine inventory' : 'Inventory'} description="Independent stock balances per warehouse and SKU. Available excludes reserved, damaged and quarantined stock." action={['OWNER', 'MANAGER'].includes(user.role) && <button onClick={() => setOpen(true)} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><SlidersHorizontal className="h-4 w-4" /> Adjust stock</button>} />
    {error && <p className="mb-4 text-red-600">{error}</p>}
    <DataTable rows={inventory} empty={loading ? 'Loading inventory…' : 'No stock records'} columns={columns} />
    <Modal title="Adjust inventory" open={open} onClose={() => setOpen(false)}>
      <form onSubmit={submit} className="grid gap-4">
        {formError && <p className="text-sm text-red-600">{formError}</p>}
        {user.role === 'OWNER' && <Select label="Warehouse" name="warehouse_id" value={form.warehouse_id} onChange={change} options={warehouses.map((item) => ({ value: item.id, label: `${item.warehouse_code} — ${item.name}` }))} />}
        <Field label="SKU" name="sku" value={form.sku} onChange={change} />
        <Field label="Quantity change" name="quantity_change" type="number" value={form.quantity_change} onChange={change} />
        <Field label="Reason" name="reason" value={form.reason} onChange={change} />
        <div className="flex justify-end"><SubmitButton busy={busy}>Apply adjustment</SubmitButton></div>
      </form>
    </Modal>
  </>
}
