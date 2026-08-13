import { X } from 'lucide-react'

export default function Modal({ title, open, onClose, children }) {
  if (!open) return null
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="dialog" aria-modal="true"><section className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"><header className="sticky top-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4"><h2 className="text-lg font-bold text-slate-950">{title}</h2><button onClick={onClose} aria-label="Close" className="rounded-lg p-2 hover:bg-slate-100"><X className="h-5 w-5" /></button></header><div className="p-6">{children}</div></section></div>
}
