import { Boxes, LogOut, Warehouse } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

export default function DashboardPlaceholder({ title, description }) {
  const { user, logout } = useAuth()
  return <main className="min-h-screen bg-slate-50"><header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4"><div className="flex items-center gap-3 font-bold"><Boxes className="text-blue-600" /> WMS</div><button onClick={logout} className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-slate-950"><LogOut className="h-4 w-4" /> Sign out</button></header><section className="mx-auto max-w-6xl p-6 lg:p-10"><div className="rounded-2xl bg-slate-950 p-8 text-white"><div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600"><Warehouse /></div><p className="mt-8 text-sm font-semibold uppercase tracking-widest text-blue-400">{user.role} workspace</p><h1 className="mt-2 text-3xl font-bold">{title}</h1><p className="mt-3 max-w-2xl text-slate-300">{description}</p><p className="mt-8 text-sm text-slate-400">Signed in as {user.first_name} {user.last_name}</p></div></section></main>
}
