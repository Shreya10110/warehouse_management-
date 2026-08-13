import { AlertTriangle, Boxes, Building2, ClipboardCheck, FileClock, HelpCircle, LayoutDashboard, PackageCheck, Settings, ShoppingCart, ShieldCheck, Truck, Users, Warehouse } from 'lucide-react'

const admin = [
  ['Dashboard', '/admin/dashboard', LayoutDashboard], ['Verification Requests', '/admin/approvals', ShieldCheck], ['Warehouses', '/admin/warehouses', Warehouse], ['Sellers', '/admin/sellers', Building2], ['Products / SKUs', '/admin/products', PackageCheck], ['Inventory', '/admin/inventory', Boxes], ['Expected Inbound', '/admin/inbound', Truck], ['Outbound Orders', '/admin/orders', ShoppingCart], ['Manager Issues', '/admin/issues', HelpCircle], ['Damage Reports', '/admin/damage', AlertTriangle], ['Employees', '/admin/employees', Users], ['Audit Logs', '/admin/audit', FileClock], ['Settings', '/admin/settings', Settings],
]
const manager = [
  ['Dashboard', '/manager/dashboard', LayoutDashboard], ['Employee Requests', '/manager/approvals', ShieldCheck], ['Inventory', '/manager/inventory', Boxes], ['Inbound Monitor', '/manager/inbound', Truck], ['Outbound Monitor', '/manager/orders', ShoppingCart], ['Report Issue', '/manager/issues', HelpCircle], ['Damage Reports', '/manager/damage', AlertTriangle], ['Team', '/manager/team', Users], ['Audit Logs', '/manager/audit', FileClock],
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
