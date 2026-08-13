export default function StatCard({ label, value, icon: Icon }) {
  return <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value ?? 0}</p></div>{Icon && <span className="rounded-lg bg-blue-50 p-2.5 text-blue-600"><Icon className="h-5 w-5" /></span>}</div></article>
}
