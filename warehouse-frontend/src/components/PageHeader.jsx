export default function PageHeader({ eyebrow, title, description, action }) {
  return <div className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{eyebrow}</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{title}</h1>{description && <p className="mt-2 max-w-2xl text-sm text-slate-500">{description}</p>}</div>{action}</div>
}
