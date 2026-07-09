// ocr-project-prep · UI Kit
// Combines sister-kit primitives with pgdp-prep job/review components.
// Token-driven · theme-swappable · every state shown.

const { useState, useEffect } = React;

// =====================================================================
// Theme toggle
// =====================================================================
function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark';
    return localStorage.getItem('theme')
      || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  });
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
  }, [theme]);
  return [theme, setTheme];
}

// =====================================================================
// Tiny helpers
// =====================================================================
function Card({ num, title, desc, children, w = '100%' }) {
  return (
    <div className="kit-card" style={{ width: w }}>
      <div className="kit-card-h">
        <span className="num">{num}</span>
        <h2>{title}</h2>
        {desc && <span className="desc">{desc}</span>}
      </div>
      <div className="kit-card-b">{children}</div>
    </div>
  );
}

function Row({ children, label, sub }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap: 8 }}>
      {(label || sub) && (
        <div style={{ display:'flex', alignItems:'baseline', gap: 10 }}>
          {label && <span className="label">{label}</span>}
          {sub && <span className="kit-sub">{sub}</span>}
        </div>
      )}
      <div className="kit-row">{children}</div>
    </div>
  );
}

function Sect({ title, children }) {
  return (
    <section style={{ marginBottom: 24 }}>
      <h3 style={{
        fontSize: 11, fontWeight: 700, letterSpacing: '0.12em',
        color: 'var(--ink-3)', textTransform: 'uppercase', margin: '0 0 12px 0',
        paddingBottom: 8, borderBottom: '1px solid var(--border-1)',
      }}>{title}</h3>
      <div style={{ display:'flex', flexDirection:'column', gap: 16 }}>{children}</div>
    </section>
  );
}

// =====================================================================
// 01 · Colors
// =====================================================================
const TOKENS = {
  surfaces: ['bg-page','bg-surface','bg-raised','bg-sunk'],
  borders:  ['border-1','border-2','border-3'],
  inks:     ['ink-1','ink-2','ink-3','ink-4'],
  accent:   ['accent','accent-ink'],
  status:   ['exact','fuzzy','mismatch','ocr','gt'],
  layers:   ['block','para','line','word'],
};

function descFor(t) {
  return ({
    'bg-page':'Page background',
    'bg-surface':'Cards, panels',
    'bg-raised':'Buttons, hover',
    'bg-sunk':'Inputs, code wells',
    'border-1':'Default',
    'border-2':'Button, input',
    'border-3':'Key cap, focus',
    'ink-1':'Primary text',
    'ink-2':'Secondary',
    'ink-3':'Hints, labels',
    'ink-4':'Disabled',
    'accent':'CTAs, focus, active',
    'accent-ink':'Text on accent',
    'exact':'OCR == GT · done',
    'fuzzy':'OCR ≈ GT · review',
    'mismatch':'OCR ≠ GT · errored',
    'ocr':'OCR-only · running',
    'gt':'GT-only · component',
    'block':'Structural block',
    'para':'Paragraph (leaf)',
    'line':'Line',
    'word':'Word',
  })[t] || '';
}

function Swatch({ tok, big }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap: 10 }}>
      <div className="swatch" style={{ background:`var(--${tok})`, width: big?64:48, height: big?64:48 }}></div>
      <div style={{ display:'flex', flexDirection:'column', gap: 2 }}>
        <span className="mono" style={{ fontSize: 11, color:'var(--ink-1)', fontWeight: 600 }}>--{tok}</span>
        <span style={{ fontSize: 10, color:'var(--ink-3)' }}>{descFor(tok)}</span>
      </div>
    </div>
  );
}

function ColorsCard() {
  return (
    <Card num="01" title="Colors" desc="All tokens. Swap theme to see both modes.">
      <Sect title="Surfaces · elevation steps">
        <Row>{TOKENS.surfaces.map(t => <Swatch key={t} tok={t}/>)}</Row>
      </Sect>
      <Sect title="Borders · 3-step">
        <Row>{TOKENS.borders.map(t => <Swatch key={t} tok={t}/>)}</Row>
      </Sect>
      <Sect title="Text · 4-step ink">
        <Row>{TOKENS.inks.map(t => <Swatch key={t} tok={t}/>)}</Row>
      </Sect>
      <Sect title="Accent">
        <Row>{TOKENS.accent.map(t => <Swatch key={t} tok={t} big/>)}</Row>
      </Sect>
      <Sect title="Status · semantic">
        <Row>{TOKENS.status.map(t => <Swatch key={t} tok={t}/>)}</Row>
      </Sect>
      <Sect title="Layers · canvas + chips">
        <Row>{TOKENS.layers.map(t => <Swatch key={t} tok={t}/>)}</Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 02 · Typography
// =====================================================================
function TypeCard() {
  const samples = [
    { role:'Section heading',  size:13,  weight:700, sample:'Line 7 · Word 1' },
    { role:'Body / button',    size:12,  weight:500, sample:'Run all dirty stages' },
    { role:'Small',            size:11,  weight:500, sample:'Open ▸' },
    { role:'Helper / hint',    size:10,  weight:400, sample:'stages out-of-date · 2m ago' },
    { role:'Label',            size:9.5, weight:700, sample:'AWAITING REVIEW', upper:true },
    { role:'Pip / chip',       size:10,  weight:600, sample:'mismatch · 42%' },
    { role:'Key cap',          size:9.5, weight:500, sample:'⌘ K', mono:true },
    { role:'Mono code',        size:11,  weight:400, sample:'scan_0033.tif · conf=0.78', mono:true },
  ];
  return (
    <Card num="02" title="Typography" desc="Inter for UI · JetBrains Mono for code-shaped · serif for page-scan only.">
      <Sect title="Families">
        <Row>
          <div style={{ display:'flex', flexDirection:'column', gap: 4, padding: 14, borderRadius: 6,
              background:'var(--bg-raised)', border:'1px solid var(--border-1)', minWidth: 260 }}>
            <span className="label">UI · Inter</span>
            <span style={{ fontFamily:'var(--ui-font)', fontSize: 22, color:'var(--ink-1)' }}>Aa Bb 0123 — chrome</span>
            <span style={{ fontFamily:'var(--ui-font)', fontSize: 12, color:'var(--ink-2)' }}>Weights 400 / 500 / 600 / 700</span>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap: 4, padding: 14, borderRadius: 6,
              background:'var(--bg-raised)', border:'1px solid var(--border-1)', minWidth: 260 }}>
            <span className="label">Code-shaped · JetBrains Mono</span>
            <span className="mono" style={{ fontSize: 22, color:'var(--ink-1)' }}>Aa Bb 0123 — OCR / IDs</span>
            <span className="mono" style={{ fontSize: 12, color:'var(--ink-2)' }}>scan_0033.tif · 7.3s · 0.78</span>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap: 4, padding: 14, borderRadius: 6,
              background:'var(--bg-raised)', border:'1px solid var(--border-1)', minWidth: 260 }}>
            <span className="label">Page-scan · serif</span>
            <span style={{ fontFamily:'serif', fontSize: 22, color:'var(--ink-1)' }}>WOODROW WILSON</span>
            <span style={{ fontSize: 10, color:'var(--ink-3)' }}>placeholder only — replace with actual scan</span>
          </div>
        </Row>
      </Sect>
      <Sect title="Scale">
        <div style={{ display:'grid', gridTemplateColumns:'170px 60px 60px 1fr', gap:'10px 14px', alignItems:'baseline' }}>
          {samples.map(s => (
            <React.Fragment key={s.role}>
              <span style={{ fontSize: 11, color:'var(--ink-2)', fontWeight: 500 }}>{s.role}</span>
              <span className="mono" style={{ fontSize: 10, color:'var(--ink-3)' }}>{s.size}px</span>
              <span className="mono" style={{ fontSize: 10, color:'var(--ink-3)' }}>{s.weight}</span>
              <span style={{
                fontFamily: s.mono ? 'var(--mono-font)' : 'var(--ui-font)',
                fontSize: s.size, fontWeight: s.weight, color:'var(--ink-1)',
                letterSpacing: s.upper ? '0.1em' : 0,
                textTransform: s.upper ? 'uppercase' : 'none',
              }}>{s.sample}</span>
            </React.Fragment>
          ))}
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 03 · Spacing & radii
// =====================================================================
function SpacingCard() {
  const space = [4,6,8,10,12,14,18,24,32];
  const radii = [3,4,5,6,8,9,12,14];
  return (
    <Card num="03" title="Spacing & radii">
      <Sect title="Spacing scale · 4-px base">
        <Row>
          {space.map(s => (
            <div key={s} style={{ display:'flex', flexDirection:'column', alignItems:'center', gap: 6 }}>
              <div style={{ width: s, height: s, background:'var(--accent)' }}></div>
              <span className="mono" style={{ fontSize: 10, color:'var(--ink-3)' }}>{s}px</span>
            </div>
          ))}
        </Row>
      </Sect>
      <Sect title="Radii">
        <Row>
          {radii.map(r => (
            <div key={r} style={{ display:'flex', flexDirection:'column', alignItems:'center', gap: 6 }}>
              <div style={{ width: 42, height: 42, background:'var(--bg-raised)',
                  border:'1px solid var(--border-2)', borderRadius: r }}></div>
              <span className="mono" style={{ fontSize: 10, color:'var(--ink-3)' }}>{r}px</span>
            </div>
          ))}
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 04 · Buttons
// =====================================================================
function ButtonsCard() {
  return (
    <Card num="04" title="Buttons" desc="Variants × sizes × states. Hover any row to see hover state.">
      <Sect title="Variants · default size">
        <Row>
          <span className="btn primary">Build package</span>
          <span className="btn">Run all dirty</span>
          <span className="btn ghost">Dismiss</span>
          <span className="btn danger">Skip page</span>
          <span className="btn icon">⚙</span>
        </Row>
      </Sect>
      <Sect title="Sizes">
        <Row>
          <span className="btn sm primary">Small</span><span className="btn sm">Small</span>
          <span className="btn primary">Default</span><span className="btn">Default</span>
          <span className="btn lg primary">Large</span><span className="btn lg">Large</span>
        </Row>
      </Sect>
      <Sect title="With icon · with hotkey · disabled">
        <Row>
          <span className="btn primary">Review next page <span className="key" style={{
            background:'rgba(0,0,0,0.25)', borderColor:'rgba(0,0,0,0.2)', color:'rgba(255,255,255,0.85)'
          }}>⏎</span></span>
          <span className="btn">◀ Prev</span>
          <span className="btn">Next ▶</span>
          <span className="btn">Open <span className="key">F</span></span>
          <span className="btn primary disabled">Build package</span>
          <span className="btn disabled">Disabled</span>
        </Row>
      </Sect>
      <Sect title="Icon buttons">
        <Row>
          <span className="btn icon sm">−</span><span className="btn icon sm">＋</span>
          <span className="btn icon">◀</span><span className="btn icon">▶</span>
          <span className="btn icon">⚙</span><span className="btn icon ghost">⋯</span>
          <span className="btn icon danger">🗑</span>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 05 · Chips & pips
// =====================================================================
function ChipsCard() {
  function Tri({ label, hot, state, kind='style', conflict }) {
    const base = `var(--${kind === 'style' ? 'ocr' : 'gt'})`;
    const m = state === 'all'
      ? { bg: `color-mix(in srgb, ${base} 10%, transparent)`, fg: base, bd: base }
      : state === 'some'
      ? { bg: 'var(--bg-raised)', fg: base, bd: base }
      : { bg: 'var(--bg-raised)', fg: 'var(--ink-2)', bd: 'var(--border-2)' };
    return (
      <span style={{
        display:'inline-flex', alignItems:'center', gap: 5,
        height: 24, padding:'0 8px 0 7px',
        background: m.bg, border:`1.5px solid ${m.bd}`, borderRadius: 12,
        fontSize: 11, fontWeight: 600, color: m.fg,
        opacity: conflict ? 0.45 : 1,
        textDecoration: conflict ? 'line-through' : 'none',
      }}>
        <span style={{
          width: 12, height: 12, borderRadius: 6,
          background: state === 'all' ? base : 'transparent',
          border:`1.5px solid ${state==='none' ? 'var(--border-3)' : base}`,
          display:'inline-flex', alignItems:'center', justifyContent:'center',
          fontSize: 8, color: 'var(--accent-ink)', fontWeight: 700,
        }}>{state === 'all' ? '✓' : ''}</span>
        <span style={{
          fontStyle: label === 'italic' ? 'italic' : 'normal',
          fontVariant: label === 'small caps' ? 'small-caps' : 'normal',
        }}>{label}</span>
        {hot && <span className="key" style={{ height:14, fontSize:9, marginLeft:2 }}>{hot}</span>}
      </span>
    );
  }
  return (
    <Card num="05" title="Chips & status pips">
      <Sect title="Static chips">
        <Row>
          <span className="chip">Active filter</span>
          <span className="chip mono">project_run_dirty</span>
          <span className="chip"><span className="dot" style={{ background:'var(--mismatch)' }}></span>mismatch 4</span>
          <span className="chip"><span className="dot" style={{ background:'var(--fuzzy)' }}></span>fuzzy 3</span>
          <span className="chip dashed">+ custom</span>
        </Row>
      </Sect>
      <Sect title="Status pips · job + match states">
        <Row>
          {[
            ['exact',   '✓', 'Done · OCR == GT'],
            ['fuzzy',   '~', 'Review · OCR ≈ GT'],
            ['mismatch','✗', 'Errored · OCR ≠ GT'],
            ['ocr',     '○', 'Running · OCR only'],
            ['gt',      '○', 'GT only'],
          ].map(([k, glyph, lbl]) => (
            <span key={k} className="pip" style={{
              background:`color-mix(in srgb, var(--${k}) 10%, transparent)`,
              color:`var(--${k})`,
              border:`1px solid color-mix(in srgb, var(--${k}) 33%, transparent)`,
            }}>
              <span className="dot" style={{ background:`var(--${k})` }}></span>
              {glyph} {lbl}
            </span>
          ))}
        </Row>
        <Row>
          <span className="pip" style={{ background:'var(--bg-raised)', color:'var(--ink-3)', border:'1px solid var(--border-2)' }}>
            <span className="dot" style={{ background:'var(--ink-4)' }}></span>○ Queued
          </span>
          <span className="pip" style={{
            background:'color-mix(in srgb, var(--ocr) 10%, transparent)',
            color:'var(--ocr)', border:'1px solid color-mix(in srgb, var(--ocr) 33%, transparent)' }}>
            <span className="dot" style={{ background:'var(--ocr)' }}></span>
            3 running
          </span>
          <span className="pip" style={{
            background:'color-mix(in srgb, var(--exact) 10%, transparent)',
            color:'var(--exact)', border:'1px solid color-mix(in srgb, var(--exact) 33%, transparent)' }}>
            <span className="dot" style={{ background:'var(--exact)' }}></span>
            28 done
          </span>
          <span className="pip" style={{
            background:'color-mix(in srgb, var(--fuzzy) 10%, transparent)',
            color:'var(--fuzzy)', border:'1px solid color-mix(in srgb, var(--fuzzy) 33%, transparent)' }}>
            <span className="dot" style={{ background:'var(--fuzzy)' }}></span>
            3 awaiting
          </span>
        </Row>
      </Sect>
      <Sect title="Tri-state chips · style (blue) · component (purple)">
        <Row>
          <Tri label="small caps" hot="S" state="all"/>
          <Tri label="italic" hot="I" state="none" conflict/>
          <Tri label="ALL CAPS" hot="C" state="some"/>
          <Tri label="blackletter" hot="B" state="all"/>
        </Row>
        <Row>
          <Tri label="drop cap" state="all" kind="component"/>
          <Tri label="footnote marker" state="none" kind="component"/>
          <Tri label="catchword" state="some" kind="component"/>
        </Row>
      </Sect>
      <Sect title="Layer chips">
        <Row>
          {['block','para','line','word'].map(l => (
            <span key={l} className="chip" style={{
              background:`color-mix(in srgb, var(--${l}) 15%, transparent)`,
              color:`var(--${l})`,
              borderColor:`color-mix(in srgb, var(--${l}) 55%, transparent)`,
              height: 24, padding:'0 10px', fontSize: 11,
            }}>
              <span className="dot" style={{ width:7, height:7, background:`var(--${l})` }}></span>
              {l === 'para' ? '¶ Paragraph' : l[0].toUpperCase()+l.slice(1)}
            </span>
          ))}
        </Row>
      </Sect>
      <Sect title="Filter chips · active state">
        <Row>
          <span className="filter-chip">All <span className="mono" style={{ color:'var(--ink-3)' }}>47</span></span>
          <span className="filter-chip">Running <span className="mono" style={{ color:'var(--ink-3)' }}>3</span></span>
          <span className="filter-chip on">Awaiting review <span className="mono" style={{ opacity:0.8 }}>3</span></span>
          <span className="filter-chip">Errored <span className="mono" style={{ color:'var(--ink-3)' }}>2</span></span>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 06 · Inputs
// =====================================================================
function InputsCard() {
  return (
    <Card num="06" title="Inputs">
      <Sect title="Text input · sizes · states">
        <Row>
          <input className="input" placeholder="default"/>
          <input className="input lg" placeholder="large" defaultValue="x:148"/>
          <input className="input" defaultValue="The" style={{
            borderColor:'var(--accent)',
            boxShadow:'0 0 0 2px color-mix(in srgb, var(--accent) 22%, transparent)' }}/>
          <input className="input" disabled placeholder="disabled"/>
          <input className="input" defaultValue="error" style={{ borderColor:'var(--mismatch)' }}/>
        </Row>
      </Sect>
      <Sect title="Search">
        <div style={{
          display:'inline-flex', alignItems:'center', gap: 8, width: 320,
          height: 30, padding:'0 12px',
          background:'var(--bg-surface)', border:'1px solid var(--border-1)',
          borderRadius: 6, color:'var(--ink-3)', fontSize: 12,
        }}>
          <span>⌕</span>
          <span style={{ flex:1 }}>Search projects, pages, jobs…</span>
          <span className="key">⌘</span><span className="key">K</span>
        </div>
      </Sect>
      <Sect title="Segmented (density / view toggle)">
        <Row>
          <div style={{ display:'flex', alignItems:'center', gap: 4, fontSize: 10, color:'var(--ink-3)' }}>
            <span>Density</span>
            <div style={{ display:'flex', background:'var(--bg-sunk)', border:'1px solid var(--border-2)', borderRadius: 4, padding: 1 }}>
              <span style={{ padding:'3px 10px', borderRadius: 3, background:'var(--bg-raised)', color:'var(--ink-1)', fontSize: 10, fontWeight: 600 }}>Cards</span>
              <span style={{ padding:'3px 10px', fontSize: 10, color:'var(--ink-3)' }}>Rows</span>
            </div>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap: 4, fontSize: 10, color:'var(--ink-3)' }}>
            <span>View</span>
            <div style={{ display:'flex', background:'var(--bg-sunk)', border:'1px solid var(--border-2)', borderRadius: 4, padding: 1 }}>
              <span style={{ padding:'3px 8px', fontSize: 10, color:'var(--ink-3)' }}>Blocks</span>
              <span style={{ padding:'3px 8px', fontSize: 10, color:'var(--ink-3)' }}>¶</span>
              <span style={{ padding:'3px 8px', fontSize: 10, color:'var(--ink-3)' }}>Lines</span>
              <span style={{ padding:'3px 8px', borderRadius: 3, background:'var(--bg-raised)', color:'var(--ink-1)', fontSize: 10, fontWeight: 600 }}>Words</span>
            </div>
          </div>
        </Row>
      </Sect>
      <Sect title="Toggle switch · checkbox">
        <Row>
          <label style={{ display:'inline-flex', alignItems:'center', gap: 8, fontSize: 11, color:'var(--ink-2)' }}>
            <span style={{
              width: 28, height: 16, borderRadius: 8,
              background:'var(--exact)', padding: 2, display:'inline-flex', alignItems:'center',
            }}>
              <span style={{ width: 12, height: 12, borderRadius: 6, background:'#fff', marginLeft:'auto' }}></span>
            </span>
            <b style={{ color:'var(--ink-1)' }}>Snap to source pixels</b>
            <span style={{ color:'var(--ink-3)' }}>integer x,y,w,h</span>
          </label>
          <label style={{ display:'inline-flex', alignItems:'center', gap: 8, fontSize: 11, color:'var(--ink-2)' }}>
            <span style={{
              width: 28, height: 16, borderRadius: 8,
              background:'var(--bg-sunk)', border:'1px solid var(--border-2)', padding: 2,
              display:'inline-flex', alignItems:'center',
            }}>
              <span style={{ width: 12, height: 12, borderRadius: 6, background:'var(--ink-3)' }}></span>
            </span>
            Auto-refine on apply
          </label>
          <label style={{ display:'inline-flex', alignItems:'center', gap: 6, fontSize: 11, color:'var(--ink-2)' }}>
            <span style={{
              width: 14, height: 14, borderRadius: 3,
              background:'var(--ink-1)', border:'1.5px solid var(--ink-1)',
              display:'inline-flex', alignItems:'center', justifyContent:'center',
              fontSize: 9, color:'var(--bg-page)', fontWeight: 700,
            }}>✓</span>
            join with space
          </label>
          <label style={{ display:'inline-flex', alignItems:'center', gap: 6, fontSize: 11, color:'var(--ink-2)' }}>
            <span style={{ width: 14, height: 14, borderRadius: 3,
              background:'var(--bg-sunk)', border:'1.5px solid var(--border-3)' }}></span>
            unchecked
          </label>
        </Row>
      </Sect>
      <Sect title="Slider (brush size)">
        <div style={{
          display:'inline-flex', alignItems:'center', gap: 8,
          padding:'6px 10px', background:'var(--bg-sunk)', border:'1px solid var(--border-2)',
          borderRadius: 6, color:'var(--ink-2)', fontSize: 11,
        }}>
          <span style={{ fontWeight: 600, color:'var(--ink-1)' }}>Brush</span>
          <div style={{ position:'relative', width: 140, height: 4, background:'var(--bg-page)', borderRadius: 2 }}>
            <div style={{ position:'absolute', inset: 0, width: '32%', background:'var(--accent)', borderRadius: 2 }}></div>
            <div style={{ position:'absolute', left:'32%', top:-3, width: 10, height: 10, borderRadius: 5,
              background:'var(--bg-surface)', border:'2px solid var(--accent)', transform:'translateX(-50%)' }}></div>
          </div>
          <span className="mono" style={{ minWidth: 32, color:'var(--ink-1)', fontWeight: 600 }}>6 px</span>
          <span style={{ fontSize: 9, color:'var(--ink-3)' }}>[ ] adjust</span>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 07 · Key caps & hotkeys
// =====================================================================
function KeysCard() {
  return (
    <Card num="07" title="Key caps">
      <Sect title="Basic">
        <Row>
          {['V','R','A','E','S','I','C','B','F','X','J','K','G','?'].map(k => <span key={k} className="key">{k}</span>)}
          <span className="key">⌘</span><span className="key">⌥</span><span className="key">⇧</span><span className="key">⌃</span>
          <span className="key">⏎</span><span className="key">␣</span><span className="key">esc</span>
          <span className="key">↑</span><span className="key">↓</span><span className="key">←</span><span className="key">→</span>
        </Row>
      </Sect>
      <Sect title="Combos">
        <Row>
          <div style={{ display:'inline-flex', gap: 3 }}><span className="key">⌘</span><span className="key">K</span></div>
          <div style={{ display:'inline-flex', gap: 3 }}><span className="key">⌥</span><span className="key">↑</span></div>
          <div style={{ display:'inline-flex', gap: 3 }}><span className="key">⌘</span><span className="key">⇧</span><span className="key">S</span></div>
          <div style={{ display:'inline-flex', gap: 3 }}><span className="key">⇧</span><span className="key">X</span></div>
          <div style={{ display:'inline-flex', gap: 3 }}><span className="key">J</span><span style={{color:'var(--ink-4)'}}>/</span><span className="key">K</span></div>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 08 · Tabs
// =====================================================================
function TabsCard() {
  function Tabs({ items, active }) {
    return (
      <div style={{ display:'flex', alignItems:'flex-end', borderBottom:'1px solid var(--border-1)' }}>
        {items.map((t, i) => {
          const on = t === active;
          return (
            <span key={i} style={{
              padding:'10px 14px', fontSize: 12.5, fontWeight: 500,
              color: on ? 'var(--ink-1)' : 'var(--ink-3)',
              borderBottom: on ? '2px solid var(--accent)' : '2px solid transparent',
              marginBottom: -1, cursor:'default',
            }}>{t}</span>
          );
        })}
      </div>
    );
  }
  return (
    <Card num="08" title="Tabs">
      <Sect title="Underline tabs · project-level">
        <div style={{ maxWidth: 540 }}>
          <Tabs items={['Overview', 'Jobs', 'Pages', 'Settings']} active="Jobs"/>
        </div>
      </Sect>
      <Sect title="With count badges">
        <div style={{ maxWidth: 540, display:'flex', alignItems:'flex-end', borderBottom:'1px solid var(--border-1)' }}>
          <span style={{ padding:'10px 14px', fontSize: 12.5, fontWeight: 500, color:'var(--ink-1)',
            borderBottom:'2px solid var(--accent)', marginBottom:-1,
            display:'inline-flex', alignItems:'center', gap: 6 }}>
            Jobs
            <span style={{ padding:'1px 6px', borderRadius: 4, fontSize: 10,
              background:'color-mix(in srgb, var(--accent) 20%, transparent)', color:'var(--accent)', fontFamily:'var(--mono-font)', fontWeight: 600 }}>3</span>
          </span>
          <span style={{ padding:'10px 14px', fontSize: 12.5, fontWeight: 500, color:'var(--ink-3)',
            display:'inline-flex', alignItems:'center', gap: 6 }}>
            Pages
            <span style={{ padding:'1px 6px', borderRadius: 4, fontSize: 10,
              background:'var(--bg-raised)', color:'var(--ink-3)', fontFamily:'var(--mono-font)' }}>47</span>
          </span>
          <span style={{ padding:'10px 14px', fontSize: 12.5, fontWeight: 500, color:'var(--ink-3)' }}>Settings</span>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 09 · Breadcrumb
// =====================================================================
function BreadcrumbCard() {
  const path = [
    { label:'projects', kind:'none' },
    { label:'willa-cather-letters', kind:'none' },
    { label:'P0033', sub:'page', kind:'block' },
    { label:'B2', sub:'block', kind:'block' },
    { label:'¶3', sub:'body', kind:'para' },
    { label:'L7', sub:'line', kind:'line' },
    { label:'W1', sub:'"The"', kind:'word' },
  ];
  function render(activeIdx) {
    return (
      <div style={{
        display:'flex', alignItems:'center', gap: 4, padding:'8px 10px',
        background:'var(--bg-page)', border:'1px solid var(--border-1)', borderRadius: 6,
      }}>
        {path.slice(0, activeIdx+1).map((p, i) => {
          const c = p.kind === 'none' ? 'var(--ink-3)' : `var(--${p.kind})`;
          const last = i === activeIdx;
          return (
            <React.Fragment key={i}>
              <span style={{
                display:'inline-flex', alignItems:'center', gap: 4,
                padding:'3px 8px', borderRadius: 4,
                background: last ? `color-mix(in srgb, ${c} 10%, transparent)` : 'transparent',
                border: last ? `1px solid color-mix(in srgb, ${c} 33%, transparent)` : '1px solid transparent',
                fontSize: 11, fontWeight: 600,
                color: last ? c : 'var(--ink-2)',
                fontFamily: p.kind !== 'none' ? 'var(--mono-font)' : 'var(--ui-font)',
              }}>
                {p.kind !== 'none' && <span style={{ width: 5, height: 5, borderRadius: 1, background: c }}></span>}
                {p.label}
                {p.sub && <span className="mono" style={{ fontSize: 9.5, color:'var(--ink-3)' }}>{p.sub}</span>}
              </span>
              {!last && <span style={{ color:'var(--ink-4)', fontSize: 11 }}>›</span>}
            </React.Fragment>
          );
        })}
        <div style={{ flex:1 }}></div>
        <span style={{ fontSize: 10, color:'var(--ink-3)' }}>
          <span className="key">⌥↑</span> parent
        </span>
      </div>
    );
  }
  return (
    <Card num="09" title="Breadcrumb" desc="Deepest segment lights up in the layer's color.">
      <Sect title="At each level">
        {render(1)}
        {render(3)}
        {render(4)}
        {render(5)}
        {render(6)}
      </Sect>
    </Card>
  );
}

// =====================================================================
// 10 · Accordions
// =====================================================================
function AccordionsCard() {
  function Acc({ label, sub, hot, accent, open }) {
    const c = accent ? `var(--${accent})` : 'var(--ink-2)';
    const bg = accent ? `color-mix(in srgb, var(--${accent}) 8%, transparent)` : 'var(--bg-sunk)';
    const bd = accent ? `color-mix(in srgb, var(--${accent}) 33%, transparent)` : 'var(--border-1)';
    return (
      <div style={{ background: bg, border:`1px solid ${bd}`, borderRadius: 6, overflow:'hidden' }}>
        <div style={{
          display:'flex', alignItems:'center', gap: 10, padding:'10px 12px',
          borderBottom: open ? `1px solid ${bd}` : 'none',
        }}>
          <span style={{
            width: 14, color: c, fontSize: 11,
            transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s',
          }}>▶</span>
          <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing:'0.05em',
            color: accent ? c : 'var(--ink-1)' }}>{label}</span>
          <span style={{ fontSize: 10, color:'var(--ink-3)' }}>{sub}</span>
          <div style={{ flex:1 }}></div>
          {hot && <span className="key">{hot}</span>}
        </div>
        {open && (
          <div style={{ padding: 12, fontSize: 11, color:'var(--ink-2)' }}>
            <em>Expanded body content lives here.</em>
          </div>
        )}
      </div>
    );
  }
  return (
    <Card num="10" title="Accordion sections">
      <Sect title="States · accent-tagged variants">
        <Acc label="BOUNDING BOX" sub="x:124 y:418 · 92×54 px" hot="F"/>
        <Acc label="REBOX" sub="redraw on zoomed region" hot="B" accent="accent" open/>
        <Acc label="ERASE PIXELS" sub="brush · rect · lasso · auto-detect" hot="X" accent="mismatch"/>
        <Acc label="STRUCTURE" sub="merge · split · neighbors"/>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 11 · Layout-type cards
// =====================================================================
function LayoutCardsCard() {
  function Glyph({ kind, active }) {
    const c = active ? 'var(--ink-1)' : 'var(--ink-3)';
    const lines = {
      h1: [{ y:18, w:30 }],
      body: [{ y:8,w:30 },{ y:16,w:32 },{ y:24,w:28 },{ y:32,w:26 }],
      quote: [{ y:8,w:24,x:6 },{ y:16,w:24,x:6 },{ y:24,w:20,x:6 }],
      column: [],
      table: 'table',
    }[kind] || [];
    return (
      <svg viewBox="0 0 38 36" width={36} height={36}>
        <rect x={1} y={1} width={36} height={34} rx={2}
          fill={active ? 'var(--bg-surface)' : 'var(--bg-sunk)'}
          stroke={active ? c : 'var(--border-2)'} strokeWidth={0.8}/>
        {lines === 'table' ? (
          <g stroke={c} strokeWidth={0.8}>
            <line x1={4} y1={10} x2={34} y2={10}/>
            <line x1={4} y1={18} x2={34} y2={18}/>
            <line x1={4} y1={26} x2={34} y2={26}/>
            <line x1={14} y1={6} x2={14} y2={30}/>
            <line x1={24} y1={6} x2={24} y2={30}/>
          </g>
        ) : kind === 'column' ? (
          <g>
            <rect x={4} y={5} width={12} height={26} fill="none" stroke={c} strokeWidth={1.2} rx={1}/>
            <rect x={22} y={5} width={12} height={26} fill="none" stroke={c} strokeWidth={1.2} rx={1} opacity={0.5}/>
          </g>
        ) : Array.isArray(lines) && lines.map((l, i) => (
          <rect key={i} x={4 + (l.x||0)} y={l.y} width={l.w} height={2} rx={1} fill={c}/>
        ))}
      </svg>
    );
  }
  function LC({ label, kind, active, hint }) {
    return (
      <div style={{
        display:'flex', flexDirection:'column', gap: 6,
        padding: 10, borderRadius: 6, minWidth: 130,
        background: active ? 'color-mix(in srgb, var(--accent) 10%, transparent)' : 'var(--bg-raised)',
        border: active ? '1.5px solid var(--accent)' : '1px solid var(--border-1)',
        position:'relative',
      }}>
        <Glyph kind={kind} active={active}/>
        <span style={{ fontSize: 11, fontWeight: 600, color: active ? 'var(--ink-1)' : 'var(--ink-2)' }}>{label}</span>
        {hint && <span style={{ fontSize: 9, color:'var(--ink-3)' }}>{hint}</span>}
        {active && (
          <span style={{
            position:'absolute', top: 6, right: 6, width: 14, height: 14, borderRadius: 7,
            background:'var(--accent)', color:'var(--accent-ink)',
            display:'inline-flex', alignItems:'center', justifyContent:'center', fontSize: 9, fontWeight: 700,
          }}>✓</span>
        )}
      </div>
    );
  }
  return (
    <Card num="11" title="Layout-type cards" desc="Used in the block / paragraph layout picker.">
      <Sect title="States">
        <Row>
          <LC label="chapter heading" kind="h1"/>
          <LC label="block quote" kind="quote" active hint="active"/>
          <LC label="body text" kind="body" hint="default"/>
          <LC label="column" kind="column"/>
          <LC label="table" kind="table"/>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 12 · Word card
// =====================================================================
function WordCardCard() {
  function WC({ idx, ocr, gt, status, sel, focused, chips=[], sc }) {
    return (
      <div style={{
        width: 160, padding: 8, borderRadius: 5,
        background: (sel||focused) ? 'var(--bg-raised)' : 'var(--bg-surface)',
        border: focused ? '1.5px solid var(--accent)' :
          sel ? '1.5px solid color-mix(in srgb, var(--accent) 40%, transparent)' :
          '1px solid var(--border-1)',
        display:'flex', flexDirection:'column', gap: 4,
      }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
          <div style={{ display:'flex', alignItems:'center', gap: 5 }}>
            <span style={{
              width: 13, height: 13, borderRadius: 3,
              background: sel ? 'var(--ink-1)' : 'var(--bg-sunk)',
              border:`1.5px solid ${sel ? 'var(--ink-1)' : 'var(--border-3)'}`,
              display:'inline-flex', alignItems:'center', justifyContent:'center',
              fontSize: 9, color:'var(--bg-page)', fontWeight: 700,
            }}>{sel ? '✓' : ''}</span>
            <span className="mono" style={{ fontSize: 9, color:'var(--ink-3)' }}>L4·W{idx}</span>
          </div>
          <span className="pip" style={{
            background:`color-mix(in srgb, var(--${status}) 10%, transparent)`,
            color:`var(--${status})`,
            border:`1px solid color-mix(in srgb, var(--${status}) 33%, transparent)`,
          }}>
            <span className="dot" style={{ background:`var(--${status})` }}></span>
            {({ exact:'✓', fuzzy:'~', mismatch:'✗' })[status]}
          </span>
        </div>
        <div style={{
          height: 38, background:'#f5efdf',
          border:'1px dashed var(--border-3)', borderRadius: 3,
          display:'flex', alignItems:'center', justifyContent:'center',
          fontFamily:'serif', fontSize: sc ? 14 : 16,
          fontVariant: sc ? 'small-caps' : 'normal',
          color:'#1a140a',
        }}>{gt}</div>
        <div className="mono" style={{
          fontSize: 10.5, color:'var(--ink-3)',
          padding:'2px 5px', background:'var(--bg-sunk)', borderRadius: 2,
          whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
        }}>{ocr}</div>
        <div className="mono" style={{
          fontSize: 10.5, color:'var(--ink-1)',
          padding:'3px 5px', background:'var(--bg-page)',
          border:`1px solid ${focused ? 'var(--accent)' : 'var(--border-2)'}`,
          borderRadius: 2,
          whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
        }}>{gt}</div>
        {chips.length > 0 && (
          <div style={{ display:'flex', gap: 3, flexWrap:'wrap' }}>
            {chips.map((c, i) => <span key={i} className="chip" style={{ fontSize: 9, height: 15, padding:'0 5px' }}>{c}</span>)}
          </div>
        )}
      </div>
    );
  }
  return (
    <Card num="12" title="Word card · canonical bulk element">
      <Sect title="States · default · selected · focused · mismatch">
        <Row>
          <WC idx={1} ocr="WOODROW" gt="WOODROW" status="exact" chips={['All Caps']}/>
          <WC idx={2} ocr="WILSON," gt="WILSON," status="exact" sel chips={['All Caps']}/>
          <WC idx={3} ocr="PH.D.," gt="Ph.D.," status="fuzzy" sel focused sc chips={['Sm. Caps']}/>
          <WC idx={4} ocr="LITT.D.," gt="Litt.D.," status="fuzzy" sc chips={['Sm. Caps']}/>
          <WC idx={5} ocr="tbe" gt="The" status="mismatch" chips={['Blackletter']}/>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 13 · Stage cells & progress
// =====================================================================
function StagesCard() {
  const STAGES = ['O','C','S','N'];
  return (
    <Card num="13" title="Stage cells · progress" desc="Mono-letter squares carry stage identity; status color carries state.">
      <Sect title="All four stage states">
        <Row>
          <div style={{ display:'inline-flex', alignItems:'center', gap: 6 }}>
            {STAGES.map(s => <span key={s} className="stage-cell s-done">{s}</span>)}
            <span className="kit-sub" style={{ marginLeft: 6 }}>done</span>
          </div>
          <div style={{ display:'inline-flex', alignItems:'center', gap: 6 }}>
            <span className="stage-cell s-done">O</span>
            <span className="stage-cell s-done">C</span>
            <span className="stage-cell s-running">S</span>
            <span className="stage-cell s-queued">N</span>
            <span className="kit-sub" style={{ marginLeft: 6 }}>running</span>
          </div>
          <div style={{ display:'inline-flex', alignItems:'center', gap: 6 }}>
            <span className="stage-cell s-done">O</span>
            <span className="stage-cell s-done">C</span>
            <span className="stage-cell s-err">S</span>
            <span className="stage-cell s-queued">N</span>
            <span className="kit-sub" style={{ marginLeft: 6 }}>errored</span>
          </div>
          <div style={{ display:'inline-flex', alignItems:'center', gap: 6 }}>
            {STAGES.map(s => <span key={s} className="stage-cell s-queued">{s}</span>)}
            <span className="kit-sub" style={{ marginLeft: 6 }}>queued</span>
          </div>
        </Row>
      </Sect>
      <Sect title="Legend">
        <Row>
          <span className="kit-sub"><b>O</b> ocr</span>
          <span className="kit-sub"><b>C</b> classify</span>
          <span className="kit-sub"><b>S</b> segment</span>
          <span className="kit-sub"><b>N</b> normalize</span>
        </Row>
      </Sect>
      <Sect title="Progress · tones">
        <div style={{ display:'flex', flexDirection:'column', gap: 10, maxWidth: 360 }}>
          <div className="progress t-done"><div className="track"><div className="fill" style={{ width:'100%' }}></div></div><span className="count">4/4</span></div>
          <div className="progress t-running"><div className="track"><div className="fill" style={{ width:'42%' }}></div></div><span className="count">28/47</span></div>
          <div className="progress t-errored"><div className="track"><div className="fill" style={{ width:'25%' }}></div></div><span className="count">1/4</span></div>
          <div className="progress t-review"><div className="track"><div className="fill" style={{ width:'75%' }}></div></div><span className="count">3/4</span></div>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 14 · Stat tiles
// =====================================================================
function StatsCard() {
  return (
    <Card num="14" title="Stat tiles" desc="Big mono numerals; tone color reserved for the metric that's blocking.">
      <Sect title="Project header row">
        <div style={{ display:'flex', background:'var(--bg-surface)', border:'1px solid var(--border-1)', borderRadius: 8, overflow:'hidden' }}>
          <div className="stat-tile">
            <div className="v" style={{ color:'var(--ink-1)' }}>47</div>
            <div className="label" style={{ marginTop: 8 }}>Total pages</div>
            <div className="mono" style={{ fontSize: 10.5, color:'var(--ink-3)', marginTop: 4 }}>scan_0001 → scan_0047</div>
          </div>
          <div style={{ width:1, background:'var(--border-1)' }}></div>
          <div className="stat-tile">
            <div className="v" style={{ color:'var(--ocr)' }}>19</div>
            <div className="label" style={{ marginTop: 8 }}>Dirty pages</div>
            <div className="mono" style={{ fontSize: 10.5, color:'var(--ink-3)', marginTop: 4 }}>stages out-of-date</div>
          </div>
          <div style={{ width:1, background:'var(--border-1)' }}></div>
          <div className="stat-tile">
            <div className="v" style={{ color:'var(--fuzzy)' }}>3</div>
            <div className="label" style={{ marginTop: 8 }}>Awaiting review</div>
            <div className="mono" style={{ fontSize: 10.5, color:'var(--ink-3)', marginTop: 4 }}>blocking build_package</div>
          </div>
          <div style={{ width:1, background:'var(--border-1)' }}></div>
          <div className="stat-tile">
            <div className="v" style={{ color:'var(--exact)' }}>28</div>
            <div className="label" style={{ marginTop: 8 }}>Ready</div>
            <div className="mono" style={{ fontSize: 10.5, color:'var(--ink-3)', marginTop: 4 }}>all stages green</div>
          </div>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 15 · Page row (jobs list)
// =====================================================================
function PageRowsCard() {
  function PR({ num, file, cells, status, doneCount, sel }) {
    return (
      <div className={`page-row ${sel ? 'sel' : ''}`}>
        <div style={{ display:'flex', alignItems:'center', gap: 10, minWidth: 0 }}>
          <span className="mk"></span>
          <div className="mono" style={{ fontSize: 11, color:'var(--ink-3)', width: 38 }}>{num}</div>
          <div className="mono" style={{ fontSize: 12, color:'var(--ink-1)', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis' }}>{file}</div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap: 4 }}>
          {cells.map((c, i) => {
            const klass = c === 'done' ? 's-done' : c === 'running' ? 's-running' : c === 'err' ? 's-err' : 's-queued';
            return <span key={i} className={`stage-cell ${klass}`}>{['O','C','S','N'][i]}</span>;
          })}
        </div>
        <div className={`progress t-${status}`}>
          <div className="track"><div className="fill" style={{ width: `${doneCount/4*100}%` }}></div></div>
          <span className="count">{doneCount}/4</span>
        </div>
        <span className="pip" style={{
          background:`color-mix(in srgb, var(--${({running:'ocr',done:'exact',errored:'mismatch',review:'fuzzy',queued:'ink-3'})[status]}) 10%, transparent)`,
          color: `var(--${({running:'ocr',done:'exact',errored:'mismatch',review:'fuzzy',queued:'ink-3'})[status]})`,
          border: `1px solid color-mix(in srgb, var(--${({running:'ocr',done:'exact',errored:'mismatch',review:'fuzzy',queued:'ink-3'})[status]}) 33%, transparent)`,
        }}>
          <span className="dot" style={{ background:`var(--${({running:'ocr',done:'exact',errored:'mismatch',review:'fuzzy',queued:'ink-3'})[status]})` }}></span>
          {({running:'Running',done:'Done',errored:'Errored',review:'Review',queued:'Queued'})[status]}
        </span>
        <span style={{ color:'var(--ink-3)' }}>›</span>
      </div>
    );
  }
  return (
    <Card num="15" title="Page rows · jobs list">
      <Sect title="All status states · with stage cells, progress, pip">
        <div style={{ border:'1px solid var(--border-1)', borderRadius: 8, overflow:'hidden', background:'var(--bg-surface)' }}>
          <PR num="0028" file="scan_0028.tif" cells={['done','done','done','done']} status="done" doneCount={4}/>
          <PR num="0029" file="scan_0029.tif" cells={['done','done','running','queued']} status="running" doneCount={2}/>
          <PR num="0032" file="scan_0032.tif" cells={['done','done','err','queued']} status="errored" doneCount={2}/>
          <PR num="0034" file="scan_0034.tif" cells={['done','done','done','done']} status="review" doneCount={4} sel/>
          <PR num="0040" file="scan_0040.tif" cells={['queued','queued','queued','queued']} status="queued" doneCount={0}/>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 16 · Toolbars (floating)
// =====================================================================
function ToolbarsCard() {
  return (
    <Card num="16" title="Floating toolbars">
      <Sect title="Mode toolbar (canvas top-right)">
        <div style={{ display:'inline-flex', gap: 3, padding: 3,
          background:'var(--bg-surface)', border:'1px solid var(--border-2)',
          borderRadius: 5, boxShadow:'0 3px 10px rgba(0,0,0,0.15)' }}>
          <span className="btn sm" style={{ background:'var(--ink-1)', color:'var(--bg-page)', borderColor:'var(--ink-1)', height: 24, padding:'0 9px', fontSize: 10 }}>⚪ Brush</span>
          <span className="btn ghost sm" style={{ height: 24, padding:'0 9px', fontSize: 10 }}>▭ Rect</span>
          <span className="btn ghost sm" style={{ height: 24, padding:'0 9px', fontSize: 10 }}>⌒ Lasso</span>
          <span className="btn ghost sm" style={{ height: 24, padding:'0 9px', fontSize: 10 }}>✋ Pan</span>
        </div>
      </Sect>
      <Sect title="Zoom toolbar (canvas bottom-center)">
        <div style={{ display:'inline-flex', alignItems:'center', gap: 4, padding: 4,
          background:'var(--bg-surface)', border:'1px solid var(--border-2)', borderRadius: 6,
          boxShadow:'0 3px 10px rgba(0,0,0,0.15)' }}>
          <span className="btn icon sm">−</span>
          <span className="mono" style={{ minWidth: 56, textAlign:'center', fontSize: 12 }}>320%</span>
          <span className="btn icon sm">＋</span>
          <div style={{ width:1, height:16, background:'var(--border-2)' }}></div>
          {['1×','2×','5×','10×'].map(z => (
            <span key={z} className="btn sm" style={{ height: 24, padding:'0 8px', fontSize: 10,
              background: z==='2×' ? 'var(--ink-1)' : 'var(--bg-raised)',
              color: z==='2×' ? 'var(--bg-page)' : 'var(--ink-1)',
              borderColor: z==='2×' ? 'var(--ink-1)' : 'var(--border-2)',
            }}>{z}</span>
          ))}
          <div style={{ width:1, height:16, background:'var(--border-2)' }}></div>
          <span className="btn sm">Fit</span>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 17 · Callouts / banners
// =====================================================================
function CalloutsCard() {
  return (
    <Card num="17" title="Callouts · banners" desc="Card tinted with status×8% bg + 35% border. Mono for any job key referenced inline.">
      <Sect title="Review needed (fuzzy)">
        <div style={{
          display:'flex', alignItems:'center', gap: 12, padding:'10px 12px 10px 14px',
          background:'color-mix(in srgb, var(--fuzzy) 8%, var(--bg-surface))',
          border:'1px solid color-mix(in srgb, var(--fuzzy) 35%, transparent)',
          borderRadius: 6, maxWidth: 760,
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: 12, background:'var(--fuzzy)',
            color:'var(--accent-ink)', display:'inline-flex', alignItems:'center', justifyContent:'center',
            fontSize: 13, fontWeight: 700,
          }}>!</span>
          <div style={{ flex:1 }}>
            <div style={{ fontSize: 12.5, fontWeight: 500, color:'var(--ink-1)' }}>3 pages need review before the package can build.</div>
            <div style={{ fontSize: 11, color:'var(--ink-3)', marginTop: 2 }}>
              <span className="mono" style={{ color:'var(--ink-2)' }}>build_package</span> is parked — resumes automatically when count reaches 0.
            </div>
          </div>
          <span className="btn sm primary">Review next →</span>
          <span className="btn ghost icon sm">✕</span>
        </div>
      </Sect>
      <Sect title="Destructive (mismatch)">
        <div style={{
          display:'flex', alignItems:'center', gap: 12, padding:'10px 12px 10px 14px',
          background:'color-mix(in srgb, var(--mismatch) 8%, var(--bg-surface))',
          border:'1px solid color-mix(in srgb, var(--mismatch) 35%, transparent)',
          borderRadius: 6, maxWidth: 760,
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: 12, background:'var(--mismatch)',
            color:'#fff', display:'inline-flex', alignItems:'center', justifyContent:'center',
            fontSize: 13, fontWeight: 700,
          }}>✕</span>
          <div style={{ flex:1 }}>
            <div style={{ fontSize: 12.5, fontWeight: 500, color:'var(--ink-1)' }}>2 pages failed during segment.</div>
            <div style={{ fontSize: 11, color:'var(--ink-3)', marginTop: 2 }}>
              <span className="mono" style={{ color:'var(--ink-2)' }}>scan_0032 · scan_0033</span> — see drawer for stack.
            </div>
          </div>
          <span className="btn sm">View errored</span>
          <span className="btn ghost icon sm">✕</span>
        </div>
      </Sect>
      <Sect title="Info (ocr)">
        <div style={{
          display:'flex', alignItems:'center', gap: 12, padding:'10px 12px 10px 14px',
          background:'color-mix(in srgb, var(--ocr) 8%, var(--bg-surface))',
          border:'1px solid color-mix(in srgb, var(--ocr) 35%, transparent)',
          borderRadius: 6, maxWidth: 760,
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: 12,
            background:'color-mix(in srgb, var(--ocr) 20%, transparent)',
            color:'var(--ocr)', border:'1px solid color-mix(in srgb, var(--ocr) 50%, transparent)',
            display:'inline-flex', alignItems:'center', justifyContent:'center',
            fontSize: 13, fontWeight: 700,
          }}>i</span>
          <div style={{ flex:1 }}>
            <div style={{ fontSize: 12.5, fontWeight: 500, color:'var(--ink-1)' }}>Re-importing 47 scans — this can take a minute.</div>
            <div style={{ fontSize: 11, color:'var(--ink-3)', marginTop: 2 }}>Dirty stages will queue automatically when import finishes.</div>
          </div>
          <span className="btn sm">View logs</span>
        </div>
      </Sect>
      <Sect title="Model suggestion (fuzzy small)">
        <div style={{
          display:'flex', alignItems:'center', gap: 10, padding:'10px 12px',
          background:'color-mix(in srgb, var(--fuzzy) 12%, transparent)',
          border:'1px solid color-mix(in srgb, var(--fuzzy) 33%, transparent)',
          borderRadius: 6, maxWidth: 640,
        }}>
          <span style={{
            width: 24, height: 24, borderRadius: 12, background:'var(--fuzzy)',
            color:'var(--accent-ink)', display:'inline-flex', alignItems:'center', justifyContent:'center',
            fontSize: 13, fontWeight: 700,
          }}>?</span>
          <span style={{ fontSize: 12, color:'var(--ink-2)' }}>
            Model suggests <b style={{ color:'var(--ink-1)' }}>block quote</b> · 71% confidence
          </span>
          <div style={{ flex:1 }}></div>
          <span className="btn sm primary">Accept ⏎</span>
          <span className="btn sm">Reject</span>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 18 · Toasts
// =====================================================================
function ToastsCard() {
  const toasts = [
    { kind:'exact',    title:'Page 46 saved', body:'22 words · all validated · 100% match' },
    { kind:'fuzzy',    title:'Rematch GT changed 3 alignments', body:'L4·W3, L7·W2, L7·W5 → review' },
    { kind:'mismatch', title:'OCR config failed', body:'Could not load rec model', actions:['Retry','Open config'] },
    { kind:'ocr',      title:'Auto-saved', body:'Local snapshot · 30s ago' },
  ];
  return (
    <Card num="18" title="Toasts">
      <Sect title="4 kinds + progress">
        <div style={{ display:'flex', flexDirection:'column', gap: 8, maxWidth: 360 }}>
          {toasts.map((t, i) => (
            <div key={i} style={{
              background:'var(--bg-surface)', border:'1px solid var(--border-1)',
              borderLeft:`4px solid var(--${t.kind})`, borderRadius: 6, padding:'10px 12px',
              display:'flex', flexDirection:'column', gap: 4,
            }}>
              <div style={{ display:'flex', alignItems:'baseline', gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>{t.title}</span>
                <span style={{ fontSize: 11, color:'var(--ink-3)' }}>✕</span>
              </div>
              <span style={{ fontSize: 11, color:'var(--ink-2)' }}>{t.body}</span>
              {t.actions && (
                <div style={{ display:'flex', gap: 6, marginTop: 4 }}>
                  {t.actions.map(a => <span key={a} className="btn sm">{a}</span>)}
                </div>
              )}
            </div>
          ))}
          <div style={{ background:'var(--bg-surface)', border:'1px solid var(--border-1)',
              borderRadius: 6, padding:'10px 12px', display:'flex', flexDirection:'column', gap: 4 }}>
            <div style={{ display:'flex', alignItems:'baseline', gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, flex: 1 }}>Building package</span>
              <span style={{ fontSize: 11, color:'var(--ink-3)' }}>✕</span>
            </div>
            <span style={{ fontSize: 11, color:'var(--ink-2)' }}>47 pages · normalizing manifest</span>
            <div style={{ height: 4, background:'var(--bg-sunk)', borderRadius: 2, marginTop: 4, position:'relative' }}>
              <div style={{ position:'absolute', inset: 0, width:'72%', background:'var(--accent)', borderRadius: 2 }}></div>
            </div>
          </div>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 19 · Nav chrome
// =====================================================================
function NavCard() {
  return (
    <Card num="19" title="Nav chrome" desc="Brand · project link · search · notification bell · avatar.">
      <Sect title="Top bar">
        <div style={{ border:'1px solid var(--border-1)', borderRadius: 8, overflow:'hidden' }}>
          <div style={{ background:'var(--bg-page)', borderBottom:'1px solid var(--border-1)' }}>
            <div style={{ padding:'0 20px', height:48, display:'flex', alignItems:'center', gap:14 }}>
              <div style={{ display:'flex', alignItems:'center', gap: 8 }}>
                <div style={{
                  width: 22, height: 22, borderRadius: 5, background:'var(--accent)', color:'var(--accent-ink)',
                  display:'inline-flex', alignItems:'center', justifyContent:'center',
                  fontFamily:'var(--mono-font)', fontWeight: 700, fontSize: 12,
                }}>p</div>
                <span className="mono" style={{ fontSize: 12, fontWeight: 600, letterSpacing:'-0.01em' }}>ocr-project-prep</span>
              </div>
              <span style={{ color:'var(--ink-4)' }}>/</span>
              <nav style={{ display:'flex', gap: 4 }}>
                <a className="nav-link">Projects</a>
                <a className="nav-link active">willa-cather-letters</a>
                <a className="nav-link">Jobs</a>
                <a className="nav-link">Settings</a>
              </nav>
              <div style={{ flex: 1 }}></div>
              <div style={{
                display:'inline-flex', alignItems:'center', gap: 6,
                height: 28, padding:'0 10px', width: 220,
                background:'var(--bg-sunk)', border:'1px solid var(--border-2)',
                borderRadius: 5, color:'var(--ink-3)', fontSize: 12,
              }}>
                <span>⌕</span>
                <span style={{ flex:1 }}>Search projects…</span>
                <span className="key">⌘K</span>
              </div>
              <button className="btn ghost icon" style={{ position:'relative' }}>
                <span style={{ fontSize: 14 }}>🔔</span>
                <span className="notif-dot">3</span>
              </button>
              <div className="avatar">M</div>
            </div>
          </div>
        </div>
      </Sect>
      <Sect title="Project header">
        <div style={{ display:'flex', flexDirection:'column', gap: 14, padding: 16,
            border:'1px solid var(--border-1)', borderRadius: 8, background:'var(--bg-surface)' }}>
          <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
            <span style={{ display:'inline-flex', alignItems:'center', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-1)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-2)' }}>projects</span>
            <span style={{ color:'var(--ink-4)', padding:'0 2px' }}>/</span>
            <span style={{ display:'inline-flex', alignItems:'center', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-2)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-1)' }}>willa-cather-letters</span>
          </div>
          <div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between', gap: 14, flexWrap:'wrap' }}>
            <div style={{ display:'flex', flexDirection:'column', gap: 6 }}>
              <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, letterSpacing:'-0.015em', color:'var(--ink-1)' }}>
                willa-cather-letters
              </h1>
              <div style={{ display:'flex', alignItems:'center', gap: 10, color:'var(--ink-3)', fontSize: 11.5 }}>
                <span><span className="mono" style={{ color:'var(--ink-2)' }}>47</span> pages</span>
                <span style={{ color:'var(--ink-4)' }}>·</span>
                <span>created <span className="mono" style={{ color:'var(--ink-2)' }}>2026-03-02</span></span>
                <span style={{ color:'var(--ink-4)' }}>·</span>
                <span>owner <span className="mono" style={{ color:'var(--ink-2)' }}>mara@</span></span>
              </div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
              <span className="btn">↻ Re-import scans</span>
              <span className="btn">▶ Run all dirty <span className="mono" style={{ color:'var(--ink-3)', fontSize: 11 }}>(19)</span></span>
              <span style={{ position:'relative' }}>
                <span className="btn primary disabled">📦 Build package</span>
                <span style={{
                  position:'absolute', top:-3, right:-3, width:10, height:10, borderRadius:5,
                  background:'var(--fuzzy)', border:'2px solid var(--bg-surface)',
                }} title="Parked"></span>
              </span>
            </div>
          </div>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 20 · Selection language
// =====================================================================
function SelectionCard() {
  return (
    <Card num="20" title="Selection language" desc="Four concurrent reads of 'what is selected'.">
      <Sect title="All four">
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap: 12 }}>
          <div style={{ padding: 14, background:'var(--bg-surface)', border:'1px solid var(--border-1)', borderRadius: 6 }}>
            <div className="label" style={{ marginBottom: 6 }}>1 · Rail target</div>
            <div style={{ display:'flex', alignItems:'center', gap: 6 }}>
              <span style={{ display:'inline-flex', alignItems:'center', padding:'3px 8px', borderRadius: 4,
                background:'color-mix(in srgb, var(--block) 10%, var(--bg-raised))',
                border:'1px solid color-mix(in srgb, var(--block) 50%, transparent)',
                color:'var(--block)', fontFamily:'var(--mono-font)', fontSize: 11, fontWeight: 600 }}>B</span>
              <span style={{ display:'inline-flex', alignItems:'center', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-1)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-2)' }}>L</span>
              <span style={{ display:'inline-flex', alignItems:'center', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-1)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-2)' }}>W</span>
            </div>
          </div>
          <div style={{ padding: 14, background:'color-mix(in srgb, var(--accent) 5%, var(--bg-surface))',
              border:'1px solid var(--accent)', boxShadow:'0 0 0 1px var(--accent) inset', borderRadius: 6 }}>
            <div className="label" style={{ marginBottom: 6, color:'var(--accent)' }}>2 · Canvas highlight</div>
            <div style={{ fontSize: 11.5, color:'var(--ink-2)' }}>2-px accent outline + 10% accent tint over the scan region.</div>
          </div>
          <div style={{ padding: 14, background:'var(--bg-surface)', border:'1px solid var(--border-1)', borderRadius: 6 }}>
            <div className="label" style={{ marginBottom: 6 }}>3 · Breadcrumb terminal</div>
            <div style={{ display:'flex', alignItems:'center', gap: 4 }}>
              <span style={{ display:'inline-flex', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-1)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-2)' }}>P0033</span>
              <span style={{ color:'var(--ink-4)' }}>›</span>
              <span style={{ display:'inline-flex', padding:'3px 8px', borderRadius: 4,
                background:'var(--bg-raised)', border:'1px solid var(--border-1)',
                fontFamily:'var(--mono-font)', fontSize: 11, color:'var(--ink-2)' }}>B2</span>
              <span style={{ color:'var(--ink-4)' }}>›</span>
              <span style={{ display:'inline-flex', padding:'3px 8px', borderRadius: 4,
                background:'color-mix(in srgb, var(--word) 10%, var(--bg-raised))',
                border:'1px solid color-mix(in srgb, var(--word) 50%, transparent)',
                color:'var(--word)', fontFamily:'var(--mono-font)', fontSize: 11, fontWeight: 600 }}>W1</span>
            </div>
          </div>
          <div style={{ padding: 14, background:'color-mix(in srgb, var(--accent) 5%, var(--bg-surface))',
              border:'1px solid var(--accent)', boxShadow:'0 0 0 1px var(--accent) inset', borderRadius: 6 }}>
            <div className="label" style={{ marginBottom: 6, color:'var(--accent)' }}>4 · Drawer row</div>
            <div style={{ display:'flex', alignItems:'center', gap: 8 }}>
              <span className="stage-cell s-done">O</span>
              <span className="mono" style={{ fontSize: 12, color:'var(--ink-1)' }}>ocr</span>
              <span style={{ flex:1 }}></span>
              <span className="mono" style={{ fontSize: 11, color:'var(--ink-3)' }}>7.3s</span>
            </div>
          </div>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 21 · Surfaces · elevation pattern
// =====================================================================
function SurfacesCard() {
  return (
    <Card num="21" title="Surfaces · elevation pattern" desc="Depth comes from stepping the surface scale; borders trace boundaries. Avoid drop shadows except floating chrome.">
      <Sect title="The four surface levels">
        <div style={{
          padding: 18, background:'var(--bg-page)',
          border:'1px solid var(--border-1)', borderRadius: 8,
        }}>
          {[
            ['bg-page',    'Page background · top header · rail',                'depth 0'],
            ['bg-surface', 'Cards · panels · drawer · right panel',               'depth 1'],
            ['bg-raised',  'Buttons · hover · active rows · chips',               'depth 2'],
            ['bg-sunk',    'Inputs · code wells · accordion · sunken sections',   'depth 3'],
          ].map(([tok, use, depth]) => (
            <div key={tok} style={{
              padding: 14, marginBottom: 8, borderRadius: 6,
              border:'1px solid var(--border-1)',
              background:`var(--${tok})`,
              display:'flex', alignItems:'center', justifyContent:'space-between',
            }}>
              <span className="mono" style={{ fontSize: 11, color:'var(--ink-2)' }}>
                <b style={{ color:'var(--ink-1)' }}>--{tok}</b> &nbsp;·&nbsp; {use}
              </span>
              <span className="label">{depth}</span>
            </div>
          ))}
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 22 · Status language
// =====================================================================
function StatusLanguageCard() {
  const items = [
    ['exact',    '✓', 'OCR == GT'],
    ['fuzzy',    '~', 'OCR ≈ GT'],
    ['mismatch', '✗', 'OCR ≠ GT'],
    ['ocr',      '○', 'only OCR (no GT)'],
    ['gt',       '○', 'only GT (no OCR)'],
  ];
  return (
    <Card num="22" title="Status language" desc="Symbol + color reads at a glance.">
      <Sect title="Legend">
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
          {items.map(([k, g, lbl]) => (
            <div key={k} style={{
              padding:'12px 14px', background:'var(--bg-surface)',
              border:'1px solid var(--border-1)', borderRadius: 6,
              display:'flex', alignItems:'center', gap: 10,
            }}>
              <span style={{
                width: 28, height: 28, borderRadius: 14,
                display:'inline-flex', alignItems:'center', justifyContent:'center',
                fontFamily:'var(--mono-font)', fontWeight: 600, fontSize: 13,
                color:`var(--${k})`,
                background:`color-mix(in srgb, var(--${k}) 12%, transparent)`,
                border:`1px solid color-mix(in srgb, var(--${k}) 40%, transparent)`,
              }}>{g}</span>
              <div style={{ fontSize: 11.5, color:'var(--ink-2)' }}>
                <b style={{ color:'var(--ink-1)' }}>{k}</b> · {lbl}
              </div>
            </div>
          ))}
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 23 · Layer color on canvas
// =====================================================================
function LayerColorCard() {
  const blendMode = 'multiply'; // light mode preferred
  return (
    <Card num="23" title="Layer color on canvas" desc="Block / paragraph / line / word overlays sit on the scan. Layer color reserved for canvas — only spills into UI as kind chips or breadcrumb terminals.">
      <Sect title="Overlays on a placeholder scan">
        <div style={{
          position:'relative',
          background:'#f5efdf',
          backgroundImage:
            'repeating-linear-gradient(0deg, rgba(20,15,5,0.04) 0 19px, transparent 19px 20px)',
          border:'1px solid var(--border-1)', borderRadius: 6,
          height: 240, overflow:'hidden', padding: 16,
        }}>
          <div style={{
            fontFamily:'serif', color:'#1a140a', opacity: 0.78,
            lineHeight: 1.55, fontSize: 15, padding:'4px 8px',
          }}>
            <div>The first letter to her brother in Red Cloud</div>
            <div>arrived on the seventh of March, 1888.</div>
            <div>She wrote in pencil, in a fast slanting hand,</div>
            <div>and her sentences ran over their lines.</div>
          </div>
          {/* block */}
          <div style={{
            position:'absolute', left: 12, top: 12, right: 12, bottom: 12,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--block) 12%, transparent)',
            border:'1.5px solid var(--block)', borderRadius: 2,
          }}></div>
          {/* paragraph */}
          <div style={{
            position:'absolute', left: 22, top: 26, right: 22,
            height: 110,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--para) 15%, transparent)',
            border:'1.5px solid var(--para)', borderRadius: 2,
          }}></div>
          {/* line */}
          <div style={{
            position:'absolute', left: 32, top: 30, right: 70,
            height: 22,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--line) 18%, transparent)',
            border:'1.5px solid var(--line)', borderRadius: 2,
          }}></div>
          {/* words */}
          <div style={{
            position:'absolute', left: 36, top: 32, width: 56, height: 18,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--word) 20%, transparent)',
            border:'1.5px solid var(--word)', borderRadius: 2,
          }}></div>
          <div style={{
            position:'absolute', left: 100, top: 32, width: 64, height: 18,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--word) 20%, transparent)',
            border:'1.5px solid var(--word)', borderRadius: 2,
          }}></div>
          <div style={{
            position:'absolute', left: 170, top: 32, width: 36, height: 18,
            mixBlendMode: blendMode,
            background:'color-mix(in srgb, var(--word) 20%, transparent)',
            border:'1.5px solid var(--word)', borderRadius: 2,
          }}></div>

          {/* layer key (floating) */}
          <div style={{
            position:'absolute', right: 14, bottom: 14,
            display:'inline-flex', gap: 6, padding: 6,
            background:'var(--bg-surface)', border:'1px solid var(--border-2)',
            borderRadius: 5, boxShadow:'0 3px 10px rgba(0,0,0,0.15)',
          }}>
            {[
              ['block','Block'], ['para','¶'], ['line','Line'], ['word','Word']
            ].map(([k, lbl]) => (
              <span key={k} className="chip" style={{
                background:`color-mix(in srgb, var(--${k}) 15%, transparent)`,
                color:`var(--${k})`,
                borderColor:`color-mix(in srgb, var(--${k}) 55%, transparent)`,
                height: 20, padding:'0 8px', fontSize: 10,
              }}>
                <span className="dot" style={{ width: 6, height: 6, background:`var(--${k})` }}></span>
                {lbl}
              </span>
            ))}
          </div>
        </div>
      </Sect>
      <Sect title="Selection states · canvas overlay">
        <Row>
          <div style={{
            position:'relative', width: 220, height: 80,
            background:'#f5efdf', border:'1px solid var(--border-1)', borderRadius: 4,
            display:'flex', alignItems:'center', justifyContent:'center',
            fontFamily:'serif', color:'#1a140a', fontSize: 18,
          }}>
            slanting hand
            <span style={{
              position:'absolute', inset: 10,
              outline:'2px solid var(--accent)',
              background:'color-mix(in srgb, var(--accent) 10%, transparent)',
              borderRadius: 2, pointerEvents:'none',
            }}></span>
            <span style={{
              position:'absolute', top:-9, left: 8,
              padding:'1px 6px', borderRadius: 3,
              background:'var(--accent)', color:'var(--accent-ink)',
              fontFamily:'var(--mono-font)', fontSize: 9, fontWeight: 700,
            }}>L7·W3 selected</span>
          </div>
          <div className="kit-sub" style={{ maxWidth: 380 }}>
            Word selection: <b>2-px accent outline + 10% accent tint</b>, plus a mono ID tag.
            Same rule at every level — the kind doesn't change the highlight color.
          </div>
        </Row>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 24 · Motion
// =====================================================================
function MotionCard() {
  const items = [
    ['Button hover',     '120 ms',  'background-color, border-color'],
    ['Tab swap',         'instant', 'no transition — tab content changes immediately'],
    ['Drawer collapse',  '180 ms',  'width transition'],
    ['Accordion expand', '200 ms',  'height + chevron rotation'],
    ['Toast enter/exit', '180 ms',  'translate-y + opacity'],
    ['Theme swap',       'instant', 'flicker is worse than a flash — no fade'],
  ];
  return (
    <Card num="24" title="Motion" desc="Short and functional. Anything > 250 ms gets in the way of a power-user tool.">
      <Sect title="Durations · easings">
        <div style={{ display:'grid', gridTemplateColumns:'180px 90px 1fr', gap:'8px 16px', alignItems:'center' }}>
          {items.map(([role, dur, note]) => (
            <React.Fragment key={role}>
              <span style={{ fontSize: 11.5, color:'var(--ink-2)', fontWeight: 500 }}>{role}</span>
              <span className="mono" style={{ fontSize: 11, color:'var(--ink-1)', fontWeight: 600 }}>{dur}</span>
              <span style={{ fontSize: 11, color:'var(--ink-3)' }}>{note}</span>
            </React.Fragment>
          ))}
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// 25 · Hotkey cheatsheet
// =====================================================================
function HotkeysCard() {
  const Group = ({ label, items }) => (
    <div style={{ display:'flex', flexDirection:'column', gap: 8 }}>
      <div className="label">{label}</div>
      {items.map(([name, ...keys], i) => (
        <div key={i} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', gap: 8 }}>
          <span style={{ fontSize: 12, color:'var(--ink-2)' }}>{name}</span>
          <div style={{ display:'inline-flex', gap: 3 }}>
            {keys.map((k, j) => <span key={j} className="key">{k}</span>)}
          </div>
        </div>
      ))}
    </div>
  );
  return (
    <Card num="25" title="Hotkey cheatsheet">
      <Sect title="By group">
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap: 24 }}>
          <Group label="Mode" items={[
            ['View','V'],['Rebox','R'],['Annotate','A'],['Erase','E']
          ]}/>
          <Group label="Target" items={[
            ['Block','1'],['Line','2'],['Word','3']
          ]}/>
          <Group label="Worklist" items={[
            ['Next item','J'],['Previous item','K'],['Mark reviewed','⌘','⏎']
          ]}/>
          <Group label="Global" items={[
            ['Command palette','⌘','K'],['Cheat sheet','⌘','/'],['Toggle theme','⇧','T']
          ]}/>
        </div>
      </Sect>
    </Card>
  );
}

// =====================================================================
// Top bar (sticky · with theme toggle)
// =====================================================================
function TopBar({ theme, setTheme }) {
  return (
    <div style={{
      position:'sticky', top: 0, zIndex: 10,
      display:'flex', alignItems:'center', gap: 12, padding:'12px 20px',
      background:'var(--bg-page)', borderBottom:'1px solid var(--border-1)',
    }}>
      <span style={{
        width: 28, height: 28, borderRadius: 6, background:'var(--accent)',
        color:'var(--accent-ink)', display:'inline-flex', alignItems:'center', justifyContent:'center',
        fontFamily:'var(--mono-font)', fontSize: 14, fontWeight: 700,
      }}>p</span>
      <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, color:'var(--ink-1)' }}>ocr-project-prep · UI Kit</h1>
      <span className="kit-sub" style={{ marginLeft: 4 }}>every primitive · every state · both themes</span>
      <div style={{ flex: 1 }}></div>
      <div className="theme-seg">
        {['dark', 'light'].map(t => (
          <button key={t} onClick={() => setTheme(t)} className={t === theme ? 'on' : ''}>
            {t === 'dark' ? '☾ Dark' : '☀ Light'}
          </button>
        ))}
      </div>
    </div>
  );
}

// =====================================================================
// App
// =====================================================================
function App() {
  const [theme, setTheme] = useTheme();
  return (
    <div>
      <TopBar theme={theme} setTheme={setTheme}/>
      <main style={{
        maxWidth: 1280, margin:'0 auto', padding:'24px 20px 80px',
        display:'flex', flexDirection:'column', gap: 24,
      }}>
        <ColorsCard/>
        <TypeCard/>
        <SpacingCard/>
        <ButtonsCard/>
        <ChipsCard/>
        <InputsCard/>
        <KeysCard/>
        <TabsCard/>
        <BreadcrumbCard/>
        <AccordionsCard/>
        <LayoutCardsCard/>
        <WordCardCard/>
        <StagesCard/>
        <StatsCard/>
        <PageRowsCard/>
        <ToolbarsCard/>
        <CalloutsCard/>
        <ToastsCard/>
        <NavCard/>
        <SelectionCard/>
        <SurfacesCard/>
        <StatusLanguageCard/>
        <LayerColorCard/>
        <MotionCard/>
        <HotkeysCard/>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App/>);
