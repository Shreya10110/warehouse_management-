import { Boxes, LoaderCircle, LockKeyhole, Mail } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { homeForRole } from '../utils/roleRoutes.js'

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={homeForRole(user.role)} replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const authenticatedUser = await login(form)
      navigate(homeForRole(authenticatedUser.role), { replace: true })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden bg-slate-950 p-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-3 text-lg font-bold"><Boxes className="text-blue-400" /> WMS</div>
        <div><p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-400">Operations, unified</p><h1 className="mt-4 max-w-xl text-5xl font-bold leading-tight">Every warehouse. Every movement. One reliable system.</h1></div>
        <p className="text-sm text-slate-400">Secure role-based access for owners, managers, inbound and outbound teams.</p>
      </section>
      <section className="flex items-center justify-center bg-slate-50 p-6">
        <form onSubmit={handleSubmit} className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-8 lg:hidden"><span className="font-bold text-slate-950">WMS</span></div>
          <h2 className="text-3xl font-bold text-slate-950">Welcome back</h2>
          <p className="mt-2 text-slate-500">Sign in to your warehouse workspace.</p>
          {error && <div role="alert" className="mt-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <label className="mt-7 block text-sm font-semibold text-slate-700">Email address<div className="relative mt-2"><Mail className="absolute left-3 top-3 h-5 w-5 text-slate-400" /><input type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-lg border border-slate-300 py-2.5 pl-11 pr-3 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" placeholder="you@company.com" /></div></label>
          <label className="mt-5 block text-sm font-semibold text-slate-700">Password<div className="relative mt-2"><LockKeyhole className="absolute left-3 top-3 h-5 w-5 text-slate-400" /><input type="password" autoComplete="current-password" required minLength="8" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="w-full rounded-lg border border-slate-300 py-2.5 pl-11 pr-3 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" placeholder="Enter your password" /></div></label>
          <button disabled={submitting} className="mt-7 flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60">{submitting && <LoaderCircle className="h-5 w-5 animate-spin" />}{submitting ? 'Signing in…' : 'Sign in'}</button>
        </form>
      </section>
    </main>
  )
}
