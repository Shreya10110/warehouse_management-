import { AlertTriangle, Boxes, ClipboardCheck, FileClock, LayoutDashboard, PackageCheck, Settings, ShoppingCart, ShieldCheck, Truck, Users, Warehouse } from 'lucide-react'

const admin = [
  ['Dashboard', '/admin/dashboard', LayoutDashboard], ['Verification Requests', '/admin/approvals', ShieldCheck], ['Warehouses', '/admin/warehouses', Warehouse], ['Inventory', '/admin/inventory', Boxes], ['Inbound', '/admin/inbound', Truck], ['Outbound Orders', '/admin/orders', ShoppingCart], ['Damage Reports', '/admin/damage', AlertTriangle], ['Products / SKUs', '/admin/products', PackageCheck], ['Employees', '/admin/employees', Users], ['Audit Logs', '/admin/audit', FileClock], ['Settings', '/admin/settings', Settings],
]
const manager = [
  ['Dashboard', '/manager/dashboard', LayoutDashboard], ['Employee Requests', '/manager/approvals', ShieldCheck], ['Inventory', '/manager/inventory', Boxes], ['Inbound', '/manager/inbound', Truck], ['Outbound Orders', '/manager/orders', ShoppingCart], ['Damage Reports', '/manager/damage', AlertTriangle], ['Team', '/manager/team', Users], ['Audit Logs', '/manager/audit', FileClock],
]
const inbound = [
  ['Dashboard', '/employee/inbound', LayoutDashboard], ['Receive Shipment', '/employee/inbound/receive', ClipboardCheck], ['Inbound Shipments', '/employee/inbound/shipments', Truck], ['Pending Inspection', '/employee/inbound/pending', FileClock], ['Damage Reports', '/employee/inbound/damage', AlertTriangle], ['Quarantine', '/employee/inbound/quarantine', Boxes],
]
const outbound = [
  ['Dashboard', '/employee/outbound', LayoutDashboard], ['Orders', '/employee/outbound/orders', ShoppingCart], ['Picking', '/employee/outbound/picking', ClipboardCheck], ['Packing', '/employee/outbound/packing', PackageCheck], ['Shipping', '/employee/outbound/shipping', Truck],
]

export function navigationForRole(role) {
  return (role === 'OWNER' ? admin : role === 'MANAGER' ? manager : role === 'INBOUND' ? inbound : outbound).map(([label, path, icon]) => ({ label, path, icon }))
}
