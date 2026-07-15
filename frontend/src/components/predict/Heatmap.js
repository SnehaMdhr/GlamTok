import { useRef, useState } from "react";
import { DAYS, ENG_MAX, TT_SCALE } from "../../theme";

/**
 * Engagement heatmap - hours across X, Mon–Sun down Y.
 * matrix: 7×24 of { norm (0..1 for color), raw (real score) }.
 * Rose intensity scale, cursor-following tooltip (positioned relative to the
 * heatmap container so the box always sits at the cursor), click-to-select.
 */
export default function Heatmap({ matrix, onCellClick, selectedCell }) {
  const [hover, setHover] = useState(null);
  const wrapRef = useRef(null);

  if (!matrix) return null;

  const cellColor = n => TT_SCALE[Math.min(TT_SCALE.length - 1, Math.max(0, Math.floor(n * TT_SCALE.length)))];

  const hours = [0, 3, 6, 9, 12, 15, 18, 21];

  // track the cursor relative to the heatmap container (not the viewport),
  // so the tooltip lands exactly where the mouse is
  const trackPos = ev => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setHover(prev => prev && { ...prev, x: ev.clientX - rect.left, y: ev.clientY - rect.top });
  };

  const tooltipStyle = () => {
    const rect = wrapRef.current?.getBoundingClientRect();
    const w = rect?.width || 600;
    const left = Math.max(6, Math.min(hover.x, w - 190));
    const top = hover.y - 64 < 0 ? hover.y + 24 : hover.y - 64;
    return { left, top };
  };

  return (
    <>
      <div className="heatmap-wrap" ref={wrapRef}>
        <div className="heat-grid">
          <div className="heat-hours">
            {hours.map(h => (
              <span key={h}>{String(h).padStart(2, "0")}h</span>
            ))}
          </div>
          {DAYS.map((day, d) => (
            <div className="heat-row" key={day}>
              <span className="heat-day">{day}</span>
              {matrix[d].map((cell, h) => {
                const isSel = selectedCell?.d === d && selectedCell?.h === h;
                return (
                  <div key={h}
                    className={isSel ? "heat-cell selected" : "heat-cell"}
                    style={{ background: cellColor(cell.norm) }}
                    onClick={() => onCellClick(d, h, cell.norm)}
                    onMouseEnter={ev => { setHover({ d, h, raw: cell.raw }); trackPos(ev); }}
                    onMouseMove={trackPos}
                    onMouseLeave={() => setHover(null)}
                  />
                );
              })}
            </div>
          ))}
        </div>

        {hover && (
          <div className="heat-tooltip" style={tooltipStyle()}>
            <span className="ht-day">
              {DAYS[hover.d]} {String(hover.h).padStart(2, "0")}:00 NPT
            </span>
            <br />
            predicted engagement <span className="ht-score">
              {((hover.raw / ENG_MAX) * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      <div className="heat-legend">
        <span>low</span>
        <div className="heat-scale" />
        <span>high</span>
        <span style={{ marginLeft: 12 }}>· click a cell to inspect</span>
      </div>
    </>
  );
}
