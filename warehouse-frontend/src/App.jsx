import { Navigate, Route, Routes } from 'react-router-dom'
import DashboardPlaceholder from './components/DashboardPlaceholder.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProtectedRoute from './routes/ProtectedRoute.jsx'

export default function App() {
  return <AuthProvider><Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<ProtectedRoute roles={['OWNER']} />}><Route path="/admin/dashboard" element={<DashboardPlaceholder title="Admin dashboard" description="Company-wide warehouse control and visibility." />} /></Route>
    <Route element={<ProtectedRoute roles={['MANAGER']} />}><Route path="/manager/dashboard" element={<DashboardPlaceholder title="Manager dashboard" description="Manage your assigned warehouse and team." />} /></Route>
    <Route element={<ProtectedRoute roles={['INBOUND']} />}><Route path="/employee/inbound" element={<DashboardPlaceholder title="Inbound workspace" description="Receive, inspect and record incoming shipments." />} /></Route>
    <Route element={<ProtectedRoute roles={['OUTBOUND']} />}><Route path="/employee/outbound" element={<DashboardPlaceholder title="Outbound workspace" description="Pick, pack and ship assigned orders." />} /></Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes></AuthProvider>
}
