import { useEffect, useRef, useState } from "react";

/** Selector con buscador: solo deja elegir opciones reales (nada de texto libre). */
export default function TagPicker({ label, values, onChange, options, placeholder }: {
  label: string; values: string[]; onChange: (v: string[]) => void; options: string[]; placeholder: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const available = options.filter((o) => !values.includes(o) && o.toLowerCase().includes(query.trim().toLowerCase()));

  return (
    <div className="field tag-picker" ref={wrapRef}>
      <label>{label}</label>
      <input value={query} autoComplete="off" placeholder={placeholder}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)} onClick={() => setOpen(true)} />
      {open && (
        <div className="tag-picker-menu">
          {available.length === 0 && <div className="tag-picker-empty">Sin coincidencias.</div>}
          {available.map((opt) => (
            <button type="button" key={opt} className="tag-picker-opt"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { onChange([...values, opt]); setQuery(""); setOpen(false); }}>
              {opt}
            </button>
          ))}
        </div>
      )}
      <div className="tag-input-list">
        {values.map((v) => (
          <span key={v} className="tag-pill">{v} <button type="button" onClick={() => onChange(values.filter((x) => x !== v))}>✕</button></span>
        ))}
      </div>
    </div>
  );
}
