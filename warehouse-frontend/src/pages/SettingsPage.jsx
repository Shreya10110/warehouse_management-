import PageHeader from '../components/PageHeader.jsx'

export default function SettingsPage() {
  return <><PageHeader eyebrow="Configuration" title="Settings" description="Environment-backed application configuration and integration readiness." /><section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="font-bold text-slate-950">Integrations</h2><div className="mt-5 grid gap-4 sm:grid-cols-2"><article className="rounded-lg border border-slate-200 p-4"><p className="font-semibold">MongoDB</p><p className="mt-1 text-sm text-slate-500">Configured through the backend environment.</p></article><article className="rounded-lg border border-slate-200 p-4"><p className="font-semibold">Cloudinary</p><p className="mt-1 text-sm text-slate-500">Configure credentials to enable damage evidence uploads.</p></article></div></section></>
}
