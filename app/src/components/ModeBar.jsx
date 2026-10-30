// ModeBar.jsx: the top-left panel. "One lens / Overlay" switch, and (in One lens mode) the four lens buttons.
export default function ModeBar({ D, s, set }) {
  const overlay = s.mode === "overlay";
  return (
    <div className="panel modebar">
      <div className="seg" role="group" aria-label="View">
        <button className={!overlay ? "on" : ""} aria-pressed={!overlay} onClick={() => set({ mode: "one" })}>One lens</button>
        <button className={overlay ? "on" : ""} aria-pressed={overlay} onClick={() => set({ mode: "overlay" })}>Overlay</button>
      </div>
      {!overlay && (
        <div className="chips" role="group" aria-label="Lens">
          {D.lenses.map(l => {
            const on = l.built && s.lens === l.id;
            return (
              <button key={l.id} className={"chip" + (on ? " on" : "")} aria-pressed={on} disabled={!l.built}
                      title={l.built ? undefined : "Not designed yet"} onClick={() => set({ lens: l.id })}>
                {/* l.thumb is a tiny line drawing of the lens's path, as a list of points */}
                {l.thumb && (
                  <svg viewBox="0 0 64 32" aria-hidden="true">
                    <polyline fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" points={l.thumb} />
                  </svg>
                )}
                {l.name}{!l.built && <> <small>to come</small></>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
