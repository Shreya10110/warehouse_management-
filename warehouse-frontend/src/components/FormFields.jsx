export function Field({ label, name, type = 'text', value, onChange, required = true, placeholder, ...inputProps }) {
  const unitLabels = { weight: 'Weight (gm)', length: 'Length (cm)', width: 'Width (cm)', height: 'Height (cm)' }
  const displayLabel = unitLabels[name] ?? label
  return <label className="block text-sm font-semibold text-slate-700">{displayLabel}{required && <span className="ml-1 text-red-600" aria-hidden="true">*</span>}<input name={name} type={type} value={value ?? ''} onChange={onChange} required={required} aria-required={required} placeholder={placeholder} {...inputProps} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2.5 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100" /></label>
}

export function Select({ label, name, value, onChange, options, required = true }) {
  return <label className="block text-sm font-semibold text-slate-700">{label}{required && <span className="ml-1 text-red-600" aria-hidden="true">*</span>}<select name={name} value={value ?? ''} onChange={onChange} required={required} aria-required={required} className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 font-normal outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"><option value="">Select…</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}

export function SubmitButton({ busy, children }) {
  return <button disabled={busy} className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">{busy ? 'Saving…' : children}</button>
}
