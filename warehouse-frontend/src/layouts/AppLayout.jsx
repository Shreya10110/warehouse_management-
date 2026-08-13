import { Boxes, ChevronDown, LogOut, Menu, Search, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../api/domain.js'
import { navigationForRole } from '../utils/navigation.js'

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [results, setResults] = useState([])
  const items = navigationForRole(user.role)

  async function runSearch(event) {
    event.preventDefault()
    if (search.trim().length < 2) return
    setResults(await api.search(search))
  }

  return <div className="min-h-screen bg-slate-50"><aside className={`fixed inset-y-0 left-0 z-40 w-72 transform bg-slate-950 text-slate-300 transition lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}><div className="flex h-20 items-center justify-between border-b border-slate-800 px-6"><div className="flex items-center gap-3 text-lg font-bold text-white"><span className="rounded-lg bg-blue-600 p-2"><Boxes className="h-5 w-5" /></span> WMS</div><button className="lg:hidden" onClick={() => setOpen(false)}><X /></button></div><nav className="space-y-1 p-4">{items.map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold transition ${isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-900 hover:text-white'}`}><Icon className="h-5 w-5" />{label}</NavLink>)}</nav><div className="absolute inset-x-0 bottom-0 border-t border-slate-800 p-4"><button onClick={() => logout().then(() => navigate('/login'))} className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold hover:bg-slate-900 hover:text-white"><LogOut className="h-5 w-5" /> Sign out</button></div></aside><div className="lg:pl-72"><header className="sticky top-0 z-30 flex h-20 items-center gap-4 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-7"><button onClick={() => setOpen(true)} className="rounded-lg p-2 lg:hidden"><Menu /></button><form onSubmit={runSearch} className="relative hidden max-w-lg flex-1 md:block"><Search className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" /><input value={search} onChange={(event) => { setSearch(event.target.value); if (!event.target.value) setResults([]) }} placeholder="Search order, shipment, SKU, employee…" className="w-full rounded-lg bg-slate-100 py-2.5 pl-11 pr-3 text-sm outline-none focus:ring-2 focus:ring-blue-200" />{results.length > 0 && <div className="absolute top-12 max-h-80 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-xl">{results.map((result) => <div key={`${result.result_type}-${result.id}`} className="rounded-lg px-3 py-2 hover:bg-slate-50"><p className="text-xs font-bold uppercase text-blue-600">{result.result_type.replaceAll('_', ' ')}</p><p className="truncate text-sm text-slate-700">{result.order_id ?? result.shipment_id ?? result.damage_report_id ?? result.sku ?? result.name ?? result.email}</p></div>)}</div>}</form><div className="ml-auto flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-sm font-semibold text-slate-900">{user.first_name} {user.last_name}</p><p className="text-xs text-slate-500">{user.role}</p></div><span className="grid h-10 w-10 place-items-center rounded-full bg-blue-100 font-bold text-blue-700">{user.first_name[0]}{user.last_name[0]}</span><ChevronDown className="h-4 w-4 text-slate-400" /></div></header><main className="p-4 sm:p-7 lg:p-9"><Outlet /></main></div></div>
}
