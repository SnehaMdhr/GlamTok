import { useState, useEffect, useRef } from "react";

/**
 * Dark-aware dropdown/select.
 * Single-select by default; pass `multi` + `selected` (array) for a
 * checkbox-style multi-select that stays open while picking.
 */
export default function Dropdown({ label, icon, value, display, options, onChange, multi, selected }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDoc(ev) { if (ref.current && !ref.current.contains(ev.target)) setOpen(false); }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const isSel = opt => multi ? selected?.includes(opt.value) : opt.value === value;
  const selectedOpt = multi ? null : options.find(o => o.value === value);

  return (
    <div ref={ref} style={{ position: "relative", zIndex: open ? 30 : 1 }}>
      <label className="dd-label">
        {icon && <i className={`ti ti-${icon}`} aria-hidden="true" />}
        {label}
      </label>
      <button type="button" className={open ? "dd-trigger open" : "dd-trigger"} onClick={() => setOpen(o => !o)}>
        <span className="dd-selected">
          {!multi && selectedOpt?.icon && <i className={`ti ti-${selectedOpt.icon}`} aria-hidden="true" />}
          <span>{display}</span>
        </span>
        <i className={`ti ti-chevron-down dd-chevron`} aria-hidden="true"
          style={{ transform: open ? "rotate(180deg)" : "none" }} />
      </button>
      {open && (
        <div className="dd-menu">
          {options.map(opt => {
            const selectedNow = isSel(opt);
            return (
              <div key={opt.value}
                className={selectedNow ? "dd-option selected" : "dd-option"}
                onClick={() => {
                  onChange(opt.value);
                  if (!multi) setOpen(false);
                }}>
                {opt.icon && <i className={`ti ti-${opt.icon}`} aria-hidden="true" />}
                <span style={{ flex: 1 }}>{opt.label}</span>
                {multi
                  ? <i className={`ti ${selectedNow ? "ti-checkbox" : "ti-square"} dd-check`} aria-hidden="true" style={selectedNow ? undefined : { color: "var(--neutral-accent)" }} />
                  : selectedNow && <i className="ti ti-check dd-check" aria-hidden="true" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
