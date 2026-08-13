import { AlertTriangle, Boxes, PackageCheck, ShieldCheck, ShoppingCart, Truck, Users, Warehouse } from 'lucide-react'
import { api } from '../api/domain.js'
import DataTable from '../components/DataTable.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatCard from '../components/StatCard.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useApi } from '../hooks/useApi.js'

const roleAudience = { OWNER: 'admin', MANAGER: 'manager', INBOUND: 'inbound', OUTBOUND: 'outbound' }

export default function DashboardPage() {
  const { user } = useAuth(); const audience = roleAudience[user.role]; const { data, loading, error } = useApi(() => api.dashboard(audience), [audience])
  if (loading) return <div className="py-20 text-center text-slate-500">Opening your Whitfield dashboard...</div>
  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">{error}</div>
  const warehouse = data.warehouse
  const cards = audience === 'outbound' ? [
    ['Reserved Orders', data.reserved, Boxes], ['Picking', data.picking, PackageCheck], ['Picked', data.picked, ShieldCheck], ['Ready to Ship', data.ready_to_ship, Truck], ['Shipped Today', data.shipped_today, ShoppingCart],
  ] : audience === 'inbound' ? [
    ["Today's Shipments", data.todays_shipments, Truck], ['Pending Inspection', data.pending_inspections, PackageCheck], ['Completed Today', data.completed_today, ShieldCheck], ['Damaged', data.damaged_items_today, AlertTriangle], ['Quarantine', data.quarantine_count, Boxes],
  ] : audience === 'manager' ? [
    ['Total SKUs', data.total_skus, PackageCheck], ['Available Stock', data.available_stock, ShieldCheck], ['Reserved Stock', data.reserved_stock, ShoppingCart], ['Damaged Stock', data.damaged_stock, AlertTriangle], ['Quarantine', data.quarantine_stock, Boxes], ['Inbound Today', data.inbound_today, Truck], ['Outbound Pending', data.outbound_pending, Warehouse], ['Team Members', data.team_size, Users],
  ] : [
    ['Total SKUs', data.total_skus, PackageCheck], ['Total Inventory', data.total_inventory, Boxes], ['Available Stock', data.available_stock, ShieldCheck], ['Reserved Stock', data.reserved_stock, ShoppingCart], ['Damaged Stock', data.damaged_stock, AlertTriangle], ['Inbound Today', data.inbound_today, Truck], ['Outbound Pending', data.outbound_pending, Warehouse],
  ]
  const greeting = audience === 'inbound' ? 'Receive accurately, inspect confidently, and keep Whitfield stock moving.' : audience === 'outbound' ? 'Pick with focus, pack with care, and send every order out strong.' : audience === 'manager' ? 'Lead your Whitfield team, verify new employees, and keep every operation on course.' : 'Whitfield Fulfillment is ready—lead the network and keep every warehouse moving.'
  return <><PageHeader eyebrow={`${user.role} workspace`} title={`Let’s have a great workday, ${user.first_name}.`} description={greeting} />{warehouse && <section className="mb-7 overflow-hidden rounded-2xl bg-slate-950 p-6 text-white"><p className="text-xs font-bold uppercase tracking-widest text-blue-400">Your verified warehouse</p><div className="mt-3 flex flex-col justify-between gap-4 md:flex-row"><div><h2 className="text-2xl font-bold">{warehouse.name}</h2><p className="mt-1 text-slate-300">{warehouse.warehouse_code}</p><p className="mt-3 text-sm text-slate-400">{[warehouse.address_line_1, warehouse.address_line_2, warehouse.city, warehouse.state, warehouse.postal_code, warehouse.country].filter(Boolean).join(', ')}</p></div><div className="text-sm text-slate-300"><p>{warehouse.contact_email}</p><p>{warehouse.contact_phone}</p></div></div></section>}<section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, icon]) => <StatCard key={label} label={label} value={value} icon={icon} />)}</section><section className="mt-8"><h2 className="mb-4 text-lg font-bold text-slate-950">Recent activity</h2><DataTable rows={data.recent_activity ?? []} columns={[{ key: 'created_at', label: 'Date & Time', render: (value) => value ? new Date(value).toLocaleString() : '—' }, { key: 'entity_type', label: 'Module' }, { key: 'action', label: 'Activity' }, { key: 'entity_id', label: 'Reference ID' }, { key: 'user_role', label: 'Performed By' }, { key: 'action', label: 'Status', render: (value) => <StatusBadge value={value} /> }]} /></section></>
}
