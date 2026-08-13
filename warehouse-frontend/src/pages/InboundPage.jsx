import { Barcode, CheckCircle2, Info, PackageCheck, Plus, ScanLine, Truck } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, Select, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

const blankReceipt = {
  warehouse_id: '', source_type: 'CARRIER', tracking_number: '', ticket_number: '',
  supplier_name: '', supplier_reference: '', sku: '', barcode: '',
  received_quantity: '', damaged_quantity: '0',
}

export default function InboundPage({ mode = 'all' }) {
  const { user } = useAuth()
  const { data = [], loading, error, reload } = useApi(api.shipments, [])
  const { data: warehouses = [] } = useApi(api.warehouses, [])
  const { data: products = [], loading: productsLoading, error: productError } = useApi(api.products, [])
  const activeProducts = useMemo(() => (products ?? []).filter((product) => product.is_active), [products])
  const assignedWarehouse = warehouses.find((warehouse) => warehouse.id === user.warehouse_id)
  const [open, setOpen] = useState(mode === 'receive')
  const [form, setForm] = useState(blankReceipt)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')

  const received = Number(form.received_quantity || 0)
  const damaged = Number(form.damaged_quantity || 0)
  const good = Math.max(received - damaged, 0)
  const selectedProduct = activeProducts.find((product) => product.sku === form.sku)
  const rows = mode === 'pending'
    ? (data ?? []).filter((row) => ['CREATED', 'INSPECTION', 'RECEIVING'].includes(row.status))
    : data ?? []

  function change(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  function selectProduct(event) {
    const product = activeProducts.find((item) => item.sku === event.target.value)
    setForm((current) => ({ ...current, sku: event.target.value, barcode: product?.barcode ?? '' }))
    setFormError('')
  }

  function scanBarcode(value, validate = false) {
    const barcode = value.trim()
    const product = activeProducts.find((item) => item.barcode === barcode)
    setForm((current) => ({ ...current, barcode: value, sku: product?.sku ?? current.sku }))
    if (validate && barcode && !product) setFormError('No product matches this barcode. Ask the owner to add it in Products / SKUs.')
    else setFormError('')
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setFormError('')
    setSuccess('')
    try {
      if (damaged > received) throw new Error('Damaged quantity cannot exceed received quantity.')
      const result = await api.completeReceiving({
        warehouse_id: user.role === 'OWNER' ? form.warehouse_id : null,
        source_type: form.source_type,
        tracking_number: form.source_type === 'CARRIER' ? form.tracking_number : null,
        ticket_number: form.source_type === 'MANUAL_DROP' ? form.ticket_number : null,
        supplier_name: form.supplier_name,
        supplier_reference: form.supplier_reference || null,
        items: [{
          sku: form.sku,
          barcode: form.barcode || null,
          received_quantity: received,
          damaged_quantity: damaged,
        }],
      })
      setOpen(false)
      setForm(blankReceipt)
      setSuccess(`${result.shipment_id} received successfully: ${good} good and ${damaged} damaged units posted.`)
      reload()
    } catch (requestError) {
      setFormError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const openReceipt = () => {
    setFormError('')
    setSuccess('')
    setOpen(true)
  }

  return <>
    <PageHeader
      eyebrow="Inbound employee workspace"
      title={mode === 'pending' ? 'Pending inbound receipts' : 'Inbound receiving'}
      description="Scan the product, record what arrived and its damage count. Whitfield handles the stock math and history automatically."
      action={<button onClick={openReceipt} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"><Plus className="h-4 w-4" /> Receive shipment</button>}
    />

    <section className="mb-7 grid gap-4 md:grid-cols-3">
      {[
        [ScanLine, 'Scan or select', 'Identify the product from the approved SKU master.'],
        [PackageCheck, 'Count and inspect', 'Enter only received and damaged quantities. Good quantity is calculated.'],
        [CheckCircle2, 'Complete receiving', 'Inventory, employee, timestamp, status and audit history are posted automatically.'],
      ].map(([Icon, title, text]) => <article key={title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><span className="grid h-10 w-10 place-items-center rounded-lg bg-blue-50 text-blue-600"><Icon className="h-5 w-5" /></span><h2 className="mt-4 font-bold text-slate-950">{title}</h2><p className="mt-2 text-sm leading-relaxed text-slate-500">{text}</p></article>)}
    </section>

    {success && <p role="status" className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">{success}</p>}
    {(error || productError) && <p role="alert" className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error || productError}</p>}

    <DataTable
      rows={rows}
      empty={loading ? 'Loading receipts...' : mode === 'pending' ? 'No pending receipts' : 'No inbound receipts yet'}
      columns={[
        { key: 'shipment_id', label: 'Receipt' },
        { key: 'supplier_name', label: 'Seller / Supplier' },
        { key: 'received_items', label: 'Product', render: (items, row) => (items?.length ? items.map((item) => item.product_name || item.sku).join(', ') : row.expected_items?.map((item) => item.sku).join(', ')) },
        { key: 'received_items', label: 'Quantity', render: (items) => items?.map((item) => `${item.received_quantity} received / ${item.damaged_quantity} damaged`).join(', ') || 'Awaiting count' },
        { key: 'tracking_number', label: 'Tracking / Ticket', render: (value, row) => value ?? row.ticket_number },
        { key: 'status', label: 'Status', render: (value) => <StatusBadge value={value} /> },
        { key: 'received_at', label: 'Received at', render: (value, row) => new Date(value ?? row.created_at).toLocaleString() },
      ]}
    />

    <Modal title="Complete inbound receiving" open={open} onClose={() => setOpen(false)}>
      <form onSubmit={submit} className="space-y-6">
        {formError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</p>}

        <div className="grid gap-3 rounded-xl border border-blue-100 bg-blue-50 p-4 sm:grid-cols-3">
          <div><p className="text-xs font-bold uppercase tracking-wide text-blue-600">Warehouse</p><p className="mt-1 font-semibold text-slate-900">{user.role === 'OWNER' ? 'Choose below' : assignedWarehouse?.name ?? 'Assigned warehouse'}</p></div>
          <div><p className="text-xs font-bold uppercase tracking-wide text-blue-600">Receiving employee</p><p className="mt-1 font-semibold text-slate-900">{user.first_name} {user.last_name}</p></div>
          <div><p className="text-xs font-bold uppercase tracking-wide text-blue-600">Date and status</p><p className="mt-1 font-semibold text-slate-900">Automatic on completion</p></div>
        </div>

        {user.role === 'OWNER' && <Select label="Warehouse" name="warehouse_id" value={form.warehouse_id} onChange={change} options={warehouses.map((warehouse) => ({ value: warehouse.id, label: `${warehouse.warehouse_code} - ${warehouse.name}` }))} />}

        <section>
          <h3 className="mb-4 flex items-center gap-2 font-bold text-slate-950"><Truck className="h-5 w-5 text-blue-600" /> Delivery details</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select label="Arrival type" name="source_type" value={form.source_type} onChange={change} options={[{ value: 'CARRIER', label: 'Carrier' }, { value: 'MANUAL_DROP', label: 'Seller drop-off' }]} />
            {form.source_type === 'CARRIER'
              ? <Field label="Tracking number" name="tracking_number" value={form.tracking_number} onChange={change} placeholder="TRK-123456" />
              : <Field label="Ticket number" name="ticket_number" value={form.ticket_number} onChange={change} placeholder="DROP-123456" />}
            <Field label="Seller / Supplier" name="supplier_name" value={form.supplier_name} onChange={change} placeholder="ABC Cosmetics" />
            <Field label="Supplier reference / PO (optional)" name="supplier_reference" value={form.supplier_reference} onChange={change} required={false} />
          </div>
        </section>

        <section className="border-t border-slate-200 pt-6">
          <h3 className="mb-1 flex items-center gap-2 font-bold text-slate-950"><Barcode className="h-5 w-5 text-blue-600" /> Product and physical count</h3>
          <p className="mb-4 text-sm text-slate-500">Use the product list or scan its UPC/barcode. Barcode scanners can type directly into the field.</p>
          {!productsLoading && activeProducts.length === 0 && <div className="mb-4 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><Info className="h-5 w-5 shrink-0" /><p>No active products exist. Ask the owner to create the product and barcode in <b>Products / SKUs</b>.</p></div>}
          <div className="grid gap-4 sm:grid-cols-2">
            <Select label="Product" name="sku" value={form.sku} onChange={selectProduct} options={activeProducts.map((product) => ({ value: product.sku, label: `${product.name} (${product.sku})` }))} />
            <Field label="UPC / Barcode (scan preferred)" name="barcode" value={form.barcode} onChange={(event) => scanBarcode(event.target.value)} onBlur={(event) => scanBarcode(event.target.value, true)} placeholder="Scan or enter barcode" inputMode="numeric" required={false} />
            <Field label="Received quantity" name="received_quantity" type="number" min="1" value={form.received_quantity} onChange={change} />
            <Field label="Damaged quantity" name="damaged_quantity" type="number" min="0" max={received || undefined} value={form.damaged_quantity} onChange={change} />
          </div>
          {selectedProduct && <p className="mt-3 text-sm text-slate-500">Selected: <b className="text-slate-900">{selectedProduct.name}</b>{selectedProduct.barcode ? ` - UPC ${selectedProduct.barcode}` : ''}</p>}
          <div className={`mt-5 rounded-xl border p-4 ${damaged > received ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">System-calculated good quantity</p>
            <p className={`mt-1 text-3xl font-black ${damaged > received ? 'text-red-700' : 'text-emerald-700'}`}>{damaged > received ? 'Invalid' : good}</p>
            <p className="mt-1 text-sm text-slate-600">{received} received - {damaged} damaged = {good} good</p>
          </div>
        </section>

        <div className="flex items-center justify-between gap-4 border-t border-slate-200 pt-5">
          <p className="max-w-md text-xs leading-relaxed text-slate-500">Completing is final. The same tracking or ticket number cannot be received twice.</p>
          <SubmitButton busy={busy || productsLoading}><span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4" /> Complete Receiving</span></SubmitButton>
        </div>
      </form>
    </Modal>
  </>
}
