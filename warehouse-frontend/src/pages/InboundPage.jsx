import { Barcode, CheckCircle2, ClipboardList, PackageSearch, Plus, Trash2, Truck } from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import { Field, Select, SubmitButton } from '../components/FormFields.jsx'
import Modal from '../components/Modal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

const expectedBlank = { warehouse_id: '', seller_id: '', source_type: 'CARRIER', tracking_number: '', supplier_reference: '' }
const lookupBlank = { source_type: 'CARRIER', tracking_number: '', ticket_number: '' }
const newExpectedItem = () => ({ sku: '', expected_quantity: '' })

export default function InboundPage({ mode = 'all' }) {
  const { user } = useAuth()
  const { data = [], loading, error, reload } = useApi(api.shipments, [])
  const { data: warehouses = [] } = useApi(api.warehouses, [])
  const { data: products = [], error: productError } = useApi(api.products, [])
  const { data: sellers = [], error: sellerError } = useApi(api.sellers, [])
  const activeProducts = useMemo(() => (products ?? []).filter((item) => item.is_active), [products])
  const activeSellers = useMemo(() => (sellers ?? []).filter((item) => item.is_active), [sellers])
  const assignedWarehouse = (warehouses ?? []).find((item) => item.id === user.warehouse_id)
  const [planning, setPlanning] = useState(false)
  const [expectedForm, setExpectedForm] = useState(expectedBlank)
  const [expectedItems, setExpectedItems] = useState([newExpectedItem()])
  const [receiving, setReceiving] = useState(mode === 'receive')
  const [lookupForm, setLookupForm] = useState(lookupBlank)
  const [shipment, setShipment] = useState(null)
  const [receiptItems, setReceiptItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const [success, setSuccess] = useState('')

  const pendingStatuses = ['EXPECTED', 'RECEIVING']
  const rows = mode === 'pending' ? (data ?? []).filter((item) => pendingStatuses.includes(item.status)) : data ?? []
  const sellerName = (id) => activeSellers.find((item) => item.id === id)?.name
  const dataError = error || (activeProducts.length === 0 ? productError : '') || (activeSellers.length === 0 ? sellerError : '')

  async function createExpected(event) {
    event.preventDefault(); setBusy(true); setFormError('')
    try {
      const skus = expectedItems.map((item) => item.sku)
      if (new Set(skus).size !== skus.length) throw new Error('Each product can appear only once.')
      const seller = activeSellers.find((item) => item.id === expectedForm.seller_id)
      const created = await api.createShipment({
        warehouse_id: expectedForm.warehouse_id, seller_id: expectedForm.seller_id,
        supplier_name: seller.name, supplier_reference: expectedForm.supplier_reference || null,
        source_type: expectedForm.source_type,
        tracking_number: expectedForm.source_type === 'CARRIER' ? expectedForm.tracking_number : null,
        ticket_number: null,
        expected_items: expectedItems.map((item) => ({ sku: item.sku, expected_quantity: Number(item.expected_quantity) })),
      })
      setPlanning(false); setExpectedForm(expectedBlank); setExpectedItems([newExpectedItem()])
      setSuccess(created.source_type === 'MANUAL_DROP' ? `Expected shipment created. Ticket: ${created.ticket_number}` : `Expected shipment ${created.shipment_id} created.`)
      reload()
    } catch (requestError) { setFormError(requestError.message) } finally { setBusy(false) }
  }

  async function findShipment(event) {
    event.preventDefault(); setBusy(true); setFormError('')
    try {
      const found = await api.lookupShipment({
        source_type: lookupForm.source_type,
        tracking_number: lookupForm.source_type === 'CARRIER' ? lookupForm.tracking_number : null,
        ticket_number: lookupForm.source_type === 'MANUAL_DROP' ? lookupForm.ticket_number : null,
      })
      setShipment(found)
      setReceiptItems(found.expected_items.map((line) => {
        const product = activeProducts.find((item) => item.sku === line.sku)
        return { sku: line.sku, product_name: product?.name ?? line.sku, barcode: product?.barcode ?? '', expected_quantity: line.expected_quantity, received_quantity: '', damaged_quantity: '0' }
      }))
    } catch (requestError) { setFormError(requestError.message) } finally { setBusy(false) }
  }

  async function complete(event) {
    event.preventDefault(); setBusy(true); setFormError('')
    try {
      const invalid = receiptItems.find((item) => Number(item.damaged_quantity) > Number(item.received_quantity))
      if (invalid) throw new Error(`${invalid.sku}: damaged quantity cannot exceed received quantity.`)
      const completed = await api.completeShipment(shipment.id, { items: receiptItems.map((item) => ({ sku: item.sku, barcode: item.barcode || null, received_quantity: Number(item.received_quantity), damaged_quantity: Number(item.damaged_quantity) })) })
      setReceiving(false); setShipment(null); setLookupForm(lookupBlank); setReceiptItems([])
      setSuccess(`${completed.shipment_id} completed. Inventory and damage records were updated automatically.`)
      reload()
    } catch (requestError) { setFormError(requestError.message) } finally { setBusy(false) }
  }

  const roleCopy = user.role === 'OWNER'
    ? ['Admin inbound planning', 'Expected inbound shipments', 'Create expected shipments and monitor Expected -> Receiving -> Completed.']
    : user.role === 'MANAGER'
      ? ['Warehouse monitoring', 'Inbound progress', `Monitor expected and completed receipts for ${assignedWarehouse?.name ?? 'your assigned warehouse'}.`]
      : ['Inbound team workspace', mode === 'pending' ? 'Pending receiving' : 'Inbound receiving', 'Find the Admin-created shipment, scan products, count, inspect, and complete receiving.']

  const action = user.role === 'OWNER'
    ? <button onClick={() => { setFormError(''); setPlanning(true) }} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Create expected shipment</button>
    : user.role === 'INBOUND'
      ? <button onClick={() => { setFormError(''); setShipment(null); setReceiving(true) }} className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white"><PackageSearch className="h-4 w-4" /> Find arriving shipment</button>
      : null

  return <>
    <PageHeader eyebrow={roleCopy[0]} title={roleCopy[1]} description={roleCopy[2]} action={action} />
    <section className="mb-7 grid gap-4 md:grid-cols-3">{[
      [ClipboardList, 'Expected', 'Admin selects seller, warehouse, products, quantities and arrival type.'],
      [Truck, 'Receiving', 'Inbound staff finds the exact shipment using tracking or ticket.'],
      [CheckCircle2, 'Completed', 'Good stock, damaged stock, employee, time and audit history update automatically.'],
    ].map(([Icon, title, text]) => <article key={title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><Icon className="h-6 w-6 text-blue-600" /><h2 className="mt-4 font-bold text-slate-950">{title}</h2><p className="mt-2 text-sm text-slate-500">{text}</p></article>)}</section>
    {success && <p className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">{success}</p>}
    {(dataError || formError) && <p className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-700">{dataError || formError}</p>}
    <DataTable rows={rows} empty={loading ? 'Loading inbound shipments...' : 'No inbound shipments found'} columns={[
      { key: 'shipment_id', label: 'Shipment' },
      { key: 'seller_id', label: 'Seller', render: (value, row) => sellerName(value) ?? row.supplier_name },
      { key: 'warehouse_id', label: 'Warehouse', render: (value) => (warehouses ?? []).find((item) => item.id === value)?.warehouse_code ?? value },
      { key: 'expected_items', label: 'Expected', render: (items) => items?.map((item) => `${item.sku} x ${item.expected_quantity}`).join(', ') },
      { key: 'received_items', label: 'Final result', render: (items) => items?.length ? items.map((item) => `${item.received_quantity} received / ${item.good_quantity} good / ${item.damaged_quantity} damaged`).join(', ') : 'Awaiting receipt' },
      { key: 'tracking_number', label: 'Tracking / Ticket', render: (value, row) => value ?? row.ticket_number },
      { key: 'status', label: 'Status', render: (value) => <StatusBadge value={value} /> },
    ]} />

    <Modal title="Create expected inbound shipment" open={planning} onClose={() => setPlanning(false)}><form onSubmit={createExpected} className="space-y-5">{formError && <p className="text-red-600">{formError}</p>}<div className="grid gap-4 sm:grid-cols-2"><Select label="Destination warehouse" name="warehouse_id" value={expectedForm.warehouse_id} onChange={(event) => setExpectedForm({ ...expectedForm, warehouse_id: event.target.value })} options={(warehouses ?? []).map((item) => ({ value: item.id, label: `${item.warehouse_code} - ${item.name}` }))} /><Select label="Seller" name="seller_id" value={expectedForm.seller_id} onChange={(event) => setExpectedForm({ ...expectedForm, seller_id: event.target.value })} options={activeSellers.map((item) => ({ value: item.id, label: `${item.seller_code} - ${item.name}` }))} /><Select label="Arrival type" name="source_type" value={expectedForm.source_type} onChange={(event) => setExpectedForm({ ...expectedForm, source_type: event.target.value })} options={[{ value: 'CARRIER', label: 'Carrier delivery' }, { value: 'MANUAL_DROP', label: 'Seller drop-off' }]} />{expectedForm.source_type === 'CARRIER' ? <Field label="Tracking number" name="tracking_number" value={expectedForm.tracking_number} onChange={(event) => setExpectedForm({ ...expectedForm, tracking_number: event.target.value })} /> : <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">The system generates the seller drop-off ticket automatically.</div>}<Field label="Supplier reference / PO (optional)" name="supplier_reference" value={expectedForm.supplier_reference} onChange={(event) => setExpectedForm({ ...expectedForm, supplier_reference: event.target.value })} required={false} /></div><section className="border-t pt-5"><div className="mb-3 flex items-center justify-between"><h3 className="font-bold">Expected products</h3><button type="button" onClick={() => setExpectedItems([...expectedItems, newExpectedItem()])} className="text-sm font-semibold text-blue-600">+ Add product</button></div><div className="space-y-3">{expectedItems.map((line, index) => <div key={index} className="grid items-end gap-3 rounded-xl bg-slate-50 p-4 sm:grid-cols-[1fr_170px_40px]"><Select label="Product" name={`sku-${index}`} value={line.sku} onChange={(event) => setExpectedItems(expectedItems.map((item, i) => i === index ? { ...item, sku: event.target.value } : item))} options={activeProducts.map((item) => ({ value: item.sku, label: `${item.name} (${item.sku})` }))} /><Field label="Expected quantity" name={`quantity-${index}`} type="number" min="1" value={line.expected_quantity} onChange={(event) => setExpectedItems(expectedItems.map((item, i) => i === index ? { ...item, expected_quantity: event.target.value } : item))} /><button type="button" disabled={expectedItems.length === 1} onClick={() => setExpectedItems(expectedItems.filter((_, i) => i !== index))} className="rounded-lg p-2 text-slate-400 hover:text-red-600 disabled:opacity-30"><Trash2 className="h-5 w-5" /></button></div>)}</div></section><div className="flex justify-end"><SubmitButton busy={busy}>Submit expected shipment</SubmitButton></div></form></Modal>

    <Modal title={shipment ? `Receive ${shipment.shipment_id}` : 'Find expected shipment'} open={receiving} onClose={() => setReceiving(false)}>{!shipment ? <form onSubmit={findShipment} className="space-y-5"><div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800"><b>Assigned warehouse:</b> {assignedWarehouse?.name ?? 'Loading...'}. Only matching shipments for this warehouse can be opened.</div><Select label="Arrival type" name="source_type" value={lookupForm.source_type} onChange={(event) => setLookupForm({ ...lookupForm, source_type: event.target.value })} options={[{ value: 'CARRIER', label: 'Carrier delivery' }, { value: 'MANUAL_DROP', label: 'Seller drop-off' }]} />{lookupForm.source_type === 'CARRIER' ? <Field label="Scan / enter tracking number" name="tracking_number" value={lookupForm.tracking_number} onChange={(event) => setLookupForm({ ...lookupForm, tracking_number: event.target.value })} /> : <Field label="Enter ticket number" name="ticket_number" value={lookupForm.ticket_number} onChange={(event) => setLookupForm({ ...lookupForm, ticket_number: event.target.value })} />}{formError && <p className="text-red-600">{formError}</p>}<div className="flex justify-end"><SubmitButton busy={busy}>Find shipment</SubmitButton></div></form> : <form onSubmit={complete} className="space-y-5"><div className="grid gap-3 rounded-xl border border-blue-100 bg-blue-50 p-4 sm:grid-cols-3"><div><p className="text-xs font-bold text-blue-600">WAREHOUSE</p><p className="font-semibold">{assignedWarehouse?.name}</p></div><div><p className="text-xs font-bold text-blue-600">SELLER</p><p className="font-semibold">{sellerName(shipment.seller_id) ?? shipment.supplier_name}</p></div><div><p className="text-xs font-bold text-blue-600">EMPLOYEE / TIME</p><p className="font-semibold">Automatic</p></div></div>{receiptItems.map((item, index) => { const received = Number(item.received_quantity || 0); const damaged = Number(item.damaged_quantity || 0); return <section key={item.sku} className="rounded-xl border border-slate-200 p-4"><div className="flex justify-between"><div><h3 className="font-bold">{item.product_name}</h3><p className="text-sm text-slate-500">{item.sku} {item.barcode ? `- UPC ${item.barcode}` : ''}</p></div><StatusBadge value={`EXPECTED ${item.expected_quantity}`} /></div><div className="mt-4 grid gap-4 sm:grid-cols-2"><Field label="Received quantity" name={`received-${index}`} type="number" min="0" value={item.received_quantity} onChange={(event) => setReceiptItems(receiptItems.map((line, i) => i === index ? { ...line, received_quantity: event.target.value } : line))} /><Field label="Damaged quantity" name={`damaged-${index}`} type="number" min="0" max={received} value={item.damaged_quantity} onChange={(event) => setReceiptItems(receiptItems.map((line, i) => i === index ? { ...line, damaged_quantity: event.target.value } : line))} /></div><div className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800"><Barcode className="mr-2 inline h-4 w-4" /> Good quantity: <b>{Math.max(received - damaged, 0)}</b> = {received} received - {damaged} damaged</div></section> })}{formError && <p className="text-red-600">{formError}</p>}<div className="flex justify-end"><SubmitButton busy={busy}>Complete receiving</SubmitButton></div></form>}</Modal>
  </>
}
