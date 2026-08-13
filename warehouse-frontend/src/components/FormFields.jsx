export function Field({ label, name, type = 'text', value, onChange, required = true, placeholder, ...inputProps }) {
  return <label className="block text-sm font-semibold text-slate-700">{label}<input name={name} type={type} value={value ?? ''} onChange={onChange} required={required} placeholder={placeholder} {...inputProps} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" /></label>
}

export function Select({ label, name, value, onChange, options, required = true }) {
  return <label className="block text-sm font-semibold text-slate-700">{label}<select name={name} value={value ?? ''} onChange={onChange} required={required} className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"><option value="">Select…</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}

export function SubmitButton({ busy, children }) {
  return <button disabled={busy} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{busy ? 'Saving…' : children}</button>
}
