import { Boxes, PackageCheck, Truck, Users } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useApi } from '../hooks/useApi.js'

export default function WarehouseDetailPage() {
  const { warehouseId } = useParams()
  const [tab, setTab] = useState('Overview')
  const { data: warehouse, loading, error } = useApi(() => api.warehouse(warehouseId), [warehouseId])
  const { data: inventory = [] } = useApi(() => api.inventory(`?warehouse=${warehouseId}`), [warehouseId])
  const { data: employees = [] } = useApi(api.users, [])
  const { data: shipments = [] } = useApi(api.shipments, [])
  const { data: orders = [] } = useApi(api.orders, [])
  const { data: damage = [] } = useApi(api.damageReports, [])
  const { data: audit = [] } = useApi(api.auditLogs, [])
  if (loading) return <p className="py-20 text-center text-slate-500">Loading warehouse…</p>
  if (error) return <p className="text-red-600">{error}</p>
  const scope = (items, field = 'warehouse_id') => items.filter((item) => item[field] === warehouseId)
  const scopedEmployees = scope(employees); const scopedShipments = scope(shipments); const scopedOrders = scope(orders, 'assigned_warehouse_id'); const scopedDamage = scope(damage); const scopedAudit = scope(audit)
  const tabs = ['Overview', 'Inventory', 'Inbound', 'Outbound', 'Employees', 'Damage Reports', 'Audit Logs']
  const tables = {
    Inventory: [inventory, [{ key: 'sku', label: 'SKU' }, { key: 'on_hand_quantity', label: 'On Hand' }, { key: 'reserved_quantity', label: 'Reserved' }, { key: 'available_quantity', label: 'Available' }]],
    Inbound: [scopedShipments, [{ key: 'shipment_id', label: 'Shipment' }, { key: 'supplier_name', label: 'Supplier' }, { key: 'status', label: 'Status', render: (v) => <StatusBadge value={v} /> }]],
    Outbound: [scopedOrders, [{ key: 'order_id', label: 'Order' }, { key: 'customer_name', label: 'Customer' }, { key: 'status', label: 'Status', render: (v) => <StatusBadge value={v} /> }]],
    Employees: [scopedEmployees, [{ key: 'first_name', label: 'Name', render: (_, r) => `${r.first_name} ${r.last_name}` }, { key: 'email', label: 'Email' }, { key: 'role', label: 'Role', render: (v) => <StatusBadge value={v} /> }]],
    'Damage Reports': [scopedDamage, [{ key: 'damage_report_id', label: 'Report' }, { key: 'sku', label: 'SKU' }, { key: 'damage_quantity', label: 'Quantity' }, { key: 'resolution_status', label: 'Status', render: (v) => <StatusBadge value={v} /> }]],
    'Audit Logs': [scopedAudit, [{ key: 'created_at', label: 'Date', render: (v) => new Date(v).toLocaleString() }, { key: 'entity_type', label: 'Module' }, { key: 'action', label: 'Action' }, { key: 'entity_id', label: 'Reference' }]],
  }
  return <><PageHeader eyebrow="Warehouse detail" title={warehouse.name} description={`${warehouse.warehouse_code} · ${[warehouse.address_line_1, warehouse.address_line_2, warehouse.city, warehouse.state, warehouse.postal_code, warehouse.country].filter(Boolean).join(', ')}`} /><section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><StatCard label="SKUs" value={inventory.length} icon={PackageCheck} /><StatCard label="On Hand" value={inventory.reduce((sum, item) => sum + item.on_hand_quantity, 0)} icon={Boxes} /><StatCard label="Inbound" value={scopedShipments.length} icon={Truck} /><StatCard label="Team" value={scopedEmployees.length} icon={Users} /></section><div className="mb-5 flex gap-2 overflow-x-auto border-b border-slate-200">{tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold ${tab === item ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'}`}>{item}</button>)}</div>{tab === 'Overview' ? <section className="grid gap-5 lg:grid-cols-2"><article className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="font-bold">Warehouse identity</h2><dl className="mt-4 grid grid-cols-2 gap-4 text-sm"><div><dt className="text-slate-500">Code</dt><dd className="font-semibold">{warehouse.warehouse_code}</dd></div><div><dt className="text-slate-500">Status</dt><dd className="mt-1"><StatusBadge value={warehouse.is_active ? 'ACTIVE' : 'INACTIVE'} /></dd></div><div><dt className="text-slate-500">Phone</dt><dd className="font-semibold">{warehouse.contact_phone}</dd></div><div><dt className="text-slate-500">Email</dt><dd className="font-semibold">{warehouse.contact_email}</dd></div></dl></article><article className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="font-bold">Team summary</h2><p className="mt-4 text-sm text-slate-600">Managers: {scopedEmployees.filter((item) => item.role === 'MANAGER').length}</p><p className="mt-2 text-sm text-slate-600">Inbound employees: {scopedEmployees.filter((item) => item.role === 'INBOUND').length}</p><p className="mt-2 text-sm text-slate-600">Outbound employees: {scopedEmployees.filter((item) => item.role === 'OUTBOUND').length}</p></article></section> : <DataTable rows={tables[tab][0]} columns={tables[tab][1]} />}</>
}
