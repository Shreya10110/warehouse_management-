import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import ApprovalsPage from './pages/ApprovalsPage.jsx'
import ProtectedRoute from './routes/ProtectedRoute.jsx'
import AppLayout from './layouts/AppLayout.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import WarehousesPage from './pages/WarehousesPage.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import EmployeesPage from './pages/EmployeesPage.jsx'
import InventoryPage from './pages/InventoryPage.jsx'
import InboundPage from './pages/InboundPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import DamageReportsPage from './pages/DamageReportsPage.jsx'
import AuditLogsPage from './pages/AuditLogsPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import WarehouseDetailPage from './pages/WarehouseDetailPage.jsx'

export default function App() {
  return <AuthProvider><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/signup" element={<SignupPage />} />
    <Route element={<ProtectedRoute roles={['OWNER', 'MANAGER', 'INBOUND', 'OUTBOUND']} />}><Route element={<AppLayout />}>
      <Route element={<ProtectedRoute roles={['OWNER']} />}>
        <Route path="/admin/dashboard" element={<DashboardPage />} />
        <Route path="/admin/warehouses" element={<WarehousesPage />} />
        <Route path="/admin/warehouses/:warehouseId" element={<WarehouseDetailPage />} />
        <Route path="/admin/inventory" element={<InventoryPage />} />
        <Route path="/admin/inbound" element={<InboundPage />} />
        <Route path="/admin/orders" element={<OrdersPage />} />
        <Route path="/admin/damage" element={<DamageReportsPage />} />
        <Route path="/admin/products" element={<ProductsPage />} />
        <Route path="/admin/employees" element={<EmployeesPage />} />
        <Route path="/admin/audit" element={<AuditLogsPage />} />
        <Route path="/admin/settings" element={<SettingsPage />} />
        <Route path="/admin/approvals" element={<ApprovalsPage />} />
      </Route>
      <Route element={<ProtectedRoute roles={['MANAGER']} />}>
        <Route path="/manager/dashboard" element={<DashboardPage />} />
        <Route path="/manager/inventory" element={<InventoryPage />} />
        <Route path="/manager/inbound" element={<InboundPage />} />
        <Route path="/manager/orders" element={<OrdersPage />} />
        <Route path="/manager/damage" element={<DamageReportsPage />} />
        <Route path="/manager/team" element={<EmployeesPage />} />
        <Route path="/manager/audit" element={<AuditLogsPage />} />
        <Route path="/manager/approvals" element={<ApprovalsPage />} />
      </Route>
      <Route element={<ProtectedRoute roles={['INBOUND']} />}>
        <Route path="/employee/inbound" element={<DashboardPage />} />
        <Route path="/employee/inbound/receive" element={<InboundPage mode="receive" />} />
        <Route path="/employee/inbound/shipments" element={<InboundPage />} />
        <Route path="/employee/inbound/pending" element={<InboundPage mode="pending" />} />
        <Route path="/employee/inbound/damage" element={<DamageReportsPage />} />
        <Route path="/employee/inbound/quarantine" element={<InventoryPage filter="?quarantine=true" />} />
      </Route>
      <Route element={<ProtectedRoute roles={['OUTBOUND']} />}>
        <Route path="/employee/outbound" element={<DashboardPage />} />
        <Route path="/employee/outbound/orders" element={<OrdersPage />} />
        <Route path="/employee/outbound/picking" element={<OrdersPage statusFilter="RESERVED,PICKING" />} />
        <Route path="/employee/outbound/packing" element={<OrdersPage statusFilter="PICKED" />} />
        <Route path="/employee/outbound/shipping" element={<OrdersPage statusFilter="PACKED" />} />
      </Route>
    </Route></Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes></AuthProvider>
}
