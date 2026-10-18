"""CSS personalizado do StegoLab (tema escuro azul-marinho + azul eléctrico/esmeralda).

Os componentes nativos do Streamlit são apenas *ajustados*; não são recriados,
para manter a acessibilidade e a estabilidade.
"""

CSS = """
<style>
:root {
  --bg: #0A1020;
  --bg-2: #0D1528;
  --card: rgba(17, 26, 46, 0.78);
  --card-solid: #111A2E;
  --border: rgba(148, 163, 184, 0.14);
  --border-strong: rgba(56, 189, 248, 0.38);
  --text: #E2E8F0;
  --muted: #94A3B8;
  --faint: #64748B;
  --blue: #38BDF8;
  --blue-2: #3B82F6;
  --emerald: #34D399;
  --emerald-2: #10B981;
  --amber: #FBBF24;
  --red: #F87171;
  --radius: 16px;
  --mono: "JetBrains Mono", "Fira Code", "Cascadia Code", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* ---------- Base ---------- */
html, body, [data-testid="stAppViewContainer"] {
  font-family: Inter, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1100px 520px at 8% -8%, rgba(59, 130, 246, 0.16), transparent 60%),
    radial-gradient(900px 480px at 100% 0%, rgba(16, 185, 129, 0.10), transparent 55%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1240px; padding-top: 1.6rem; padding-bottom: 2rem; }

h1, h2, h3, h4 { letter-spacing: -0.01em; }
::selection { background: rgba(56, 189, 248, 0.35); }

/* ---------- Cabeçalho ---------- */
/* Barra de cabeçalho (st.container key="headerbar"), fixa no topo ao rolar */
/* O Streamlit envolve o contentor num stLayoutWrapper: é esse que fica fixo. */
[data-testid="stLayoutWrapper"]:has(> .st-key-headerbar) { position: sticky; top: 0.5rem; z-index: 50; }
.st-key-headerbar {
  padding: 0.9rem 1.3rem; margin-bottom: 1.1rem;
  border: 1px solid var(--border); border-radius: calc(var(--radius) + 4px);
  background: linear-gradient(135deg, rgba(17, 26, 46, 0.97), rgba(13, 21, 40, 0.94));
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 40px -24px rgba(0, 0, 0, 0.85);
  animation: sl-fade 0.5s ease both;
}
.st-key-headerbar .stButton > button[kind="primary"] { animation: sl-pulse 2.4s ease-in-out 3; }
@keyframes sl-pulse {
  0%, 100% { box-shadow: 0 10px 24px -14px rgba(56, 189, 248, 0.9); }
  50% { box-shadow: 0 0 0 6px rgba(52, 211, 153, 0.18), 0 10px 24px -14px rgba(56, 189, 248, 0.9); }
}
.sl-brand { display: flex; align-items: center; gap: 1rem; }
.sl-logo { width: 54px; height: 54px; flex: none; filter: drop-shadow(0 6px 14px rgba(56, 189, 248, 0.25)); }
.sl-title { margin: 0; font-size: 1.85rem; font-weight: 800; line-height: 1.1; color: var(--text); }
.sl-title span {
  background: linear-gradient(90deg, var(--blue), var(--emerald));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.sl-subtitle { margin: 0.2rem 0 0; color: var(--muted); font-size: 0.98rem; }
.sl-tag { text-align: right; color: var(--faint); font-size: 0.76rem; line-height: 1.5; margin-top: 0.15rem; }
.sl-tag b { color: var(--muted); font-weight: 600; }

/* ---------- Separadores ---------- */
[data-testid="stTabs"] [role="tablist"] {
  gap: 0.35rem; padding: 0.35rem; border-radius: 14px; border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.7); flex-wrap: wrap; box-shadow: none;
}
[data-testid="stTabs"] [role="tablist"]::after { display: none; }
[data-testid="stTab"] {
  height: auto !important; padding: 0.55rem 1rem !important; margin: 0 !important; border-radius: 10px;
  color: var(--muted); transition: background 0.2s ease, color 0.2s ease;
}
[data-testid="stTab"]:hover { background: rgba(56, 189, 248, 0.08); color: var(--text); }
[data-testid="stTab"][aria-selected="true"] {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.24), rgba(16, 185, 129, 0.18));
  color: var(--text); box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.25);
}
[data-testid="stTab"] p { font-weight: 600; }
[data-testid="stTabs"] .react-aria-SelectionIndicator { display: none; }
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 1.1rem; }

/* ---------- Cartões (st.container com key="card_...") ---------- */
[class*="st-key-card"] {
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 1.15rem 1.25rem 1.25rem; backdrop-filter: blur(6px);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  animation: sl-fade 0.45s ease both;
}
[class*="st-key-card"]:hover {
  border-color: rgba(56, 189, 248, 0.26);
  box-shadow: 0 14px 34px -26px rgba(56, 189, 248, 0.6);
}
[class*="st-key-cardresult"] { border-color: rgba(52, 211, 153, 0.35); }

.sl-step { display: flex; align-items: center; gap: 0.65rem; margin: 0 0 0.6rem; }
.sl-step-num {
  display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 9px;
  font-size: 0.85rem; font-weight: 700; color: #04121F;
  background: linear-gradient(135deg, var(--blue), var(--emerald));
}
.sl-step-title { font-size: 1.05rem; font-weight: 700; color: var(--text); }
.sl-step-hint { color: var(--faint); font-size: 0.82rem; margin-left: auto; }

/* ---------- Pequenas etiquetas de metadados ---------- */
.sl-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.6rem 0 0.2rem; }
.sl-chip {
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.78rem;
  color: var(--muted); background: rgba(148, 163, 184, 0.08); border: 1px solid var(--border);
}
.sl-chip b { color: var(--text); font-weight: 600; font-family: var(--mono); font-size: 0.76rem; }
.sl-chip.ok { border-color: rgba(52, 211, 153, 0.35); color: var(--emerald); }
.sl-chip.lock { border-color: rgba(251, 191, 36, 0.35); color: var(--amber); }

/* ---------- Barra de capacidade ---------- */
.sl-meter { margin: 0.4rem 0 0.9rem; }
.sl-meter-top { display: flex; justify-content: space-between; font-size: 0.82rem; color: var(--muted); margin-bottom: 0.35rem; }
.sl-meter-top b { color: var(--text); font-family: var(--mono); font-weight: 600; }
.sl-meter-track { height: 10px; border-radius: 999px; background: rgba(148, 163, 184, 0.12); overflow: hidden; }
.sl-meter-fill {
  height: 100%; border-radius: 999px; min-width: 3px;
  background: linear-gradient(90deg, var(--emerald-2), var(--blue));
  transition: width 0.5s cubic-bezier(.2, .8, .2, 1);
}
.sl-meter.warn .sl-meter-fill { background: linear-gradient(90deg, var(--amber), #F59E0B); }
.sl-meter.over .sl-meter-fill { background: linear-gradient(90deg, #EF4444, var(--red)); }
.sl-meter-foot { font-size: 0.75rem; color: var(--faint); margin-top: 0.3rem; }

.sl-counter { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--faint); margin: -0.35rem 0 0.8rem; }
.sl-counter b { color: var(--muted); font-family: var(--mono); }

/* ---------- Notificações ---------- */
.sl-notice {
  display: flex; gap: 0.75rem; align-items: flex-start;
  padding: 0.8rem 1rem; border-radius: 12px; margin: 0.4rem 0 0.8rem;
  border: 1px solid var(--border); background: rgba(148, 163, 184, 0.06);
  font-size: 0.9rem; color: var(--text); animation: sl-fade 0.35s ease both;
}
.sl-notice .ico { flex: none; width: 22px; height: 22px; border-radius: 7px; display: grid; place-items: center; font-size: 0.8rem; font-weight: 800; }
.sl-notice .t { font-weight: 700; margin-bottom: 0.1rem; }
.sl-notice .d { color: var(--muted); }
.sl-notice.success { border-color: rgba(52, 211, 153, 0.4); background: rgba(16, 185, 129, 0.08); }
.sl-notice.success .ico { background: rgba(52, 211, 153, 0.18); color: var(--emerald); }
.sl-notice.info { border-color: rgba(56, 189, 248, 0.4); background: rgba(56, 189, 248, 0.07); }
.sl-notice.info .ico { background: rgba(56, 189, 248, 0.18); color: var(--blue); }
.sl-notice.warning { border-color: rgba(251, 191, 36, 0.4); background: rgba(251, 191, 36, 0.07); }
.sl-notice.warning .ico { background: rgba(251, 191, 36, 0.18); color: var(--amber); }
.sl-notice.error { border-color: rgba(248, 113, 113, 0.45); background: rgba(239, 68, 68, 0.08); }
.sl-notice.error .ico { background: rgba(248, 113, 113, 0.18); color: var(--red); }

/* ---------- Mensagem recuperada ---------- */
.sl-secret {
  font-family: var(--mono); font-size: 0.95rem; line-height: 1.6; color: #D1FAE5;
  white-space: pre-wrap; word-break: break-word; max-height: 340px; overflow: auto;
  padding: 1rem 1.1rem; border-radius: 12px;
  background: rgba(2, 6, 23, 0.65); border: 1px solid rgba(52, 211, 153, 0.3);
  box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.05);
}

/* ---------- Imagens / pré-visualizações ---------- */
[data-testid="stImage"] img, [data-testid="stImageContainer"] img {
  border-radius: 12px; border: 1px solid var(--border);
  background:
    repeating-conic-gradient(rgba(148,163,184,.08) 0% 25%, transparent 0% 50%) 50% / 16px 16px;
}
[data-testid="stImageCaption"], [data-testid="caption"] { color: var(--faint) !important; }
.sl-empty {
  display: grid; place-items: center; text-align: center; gap: 0.3rem;
  min-height: 170px; border-radius: 12px; color: var(--faint); font-size: 0.86rem;
  border: 1px dashed rgba(148, 163, 184, 0.22); background: rgba(2, 6, 23, 0.25);
}
.sl-empty svg { opacity: 0.6; }

/* ---------- Uploader ---------- */
[data-testid="stFileUploaderDropzone"] {
  border-radius: 12px; border: 1px dashed rgba(56, 189, 248, 0.35);
  background: rgba(56, 189, 248, 0.04); transition: background 0.2s ease, border-color 0.2s ease;
}
[data-testid="stFileUploaderDropzone"]:hover { background: rgba(56, 189, 248, 0.08); border-color: var(--blue); }

/* ---------- Botões ---------- */
.stButton > button, .stDownloadButton > button {
  border-radius: 11px; font-weight: 600; transition: transform 0.15s ease, box-shadow 0.2s ease, filter 0.2s ease;
}
.stButton > button:hover:not(:disabled), .stDownloadButton > button:hover:not(:disabled) { transform: translateY(-1px); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  border: 0; color: #04121F;
  background: linear-gradient(135deg, var(--blue) 0%, var(--emerald) 100%);
  box-shadow: 0 10px 24px -14px rgba(56, 189, 248, 0.9);
}
.stButton > button[kind="primary"]:hover:not(:disabled), .stDownloadButton > button[kind="primary"]:hover:not(:disabled) {
  filter: brightness(1.08); color: #04121F;
}
.stButton > button[kind="primary"]:disabled { opacity: 0.45; }

/* ---------- Campos ---------- */
.stTextArea textarea, .stTextInput input { font-size: 0.95rem; }
.stTextArea textarea { font-family: var(--mono); line-height: 1.55; }

/* ---------- Estatísticas ---------- */
.sl-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.6rem; margin: 0.4rem 0 0.9rem; }
.sl-stat { padding: 0.7rem 0.85rem; border-radius: 12px; background: rgba(2, 6, 23, 0.35); border: 1px solid var(--border); }
.sl-stat .k { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--faint); }
.sl-stat .v { font-size: 1.15rem; font-weight: 700; color: var(--text); font-family: var(--mono); margin-top: 0.15rem; }

/* ---------- Secção "Como funciona" ---------- */
.sl-flow { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.7rem; margin: 0.3rem 0 0.6rem; }
.sl-flow-step { padding: 0.9rem; border-radius: 14px; background: rgba(2, 6, 23, 0.35); border: 1px solid var(--border); }
.sl-flow-step .n { font-family: var(--mono); color: var(--blue); font-size: 0.78rem; }
.sl-flow-step .h { font-weight: 700; margin: 0.2rem 0 0.25rem; }
.sl-flow-step .p { color: var(--muted); font-size: 0.86rem; line-height: 1.45; }

.sl-bits { font-family: var(--mono); font-size: 1.02rem; letter-spacing: 0.06em; }
.sl-bits .lsb { color: #04121F; background: var(--emerald); border-radius: 4px; padding: 0 3px; font-weight: 700; }
.sl-bits .lsb.changed { background: var(--amber); }
.sl-bits .hi { color: var(--muted); }

.sl-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.sl-table th { text-align: left; color: var(--faint); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--border); }
.sl-table td { padding: 0.55rem 0.6rem; border-bottom: 1px solid rgba(148, 163, 184, 0.07); color: var(--text); vertical-align: middle; }
.sl-table td.mono { font-family: var(--mono); }
.sl-swatch { display: inline-block; width: 64px; height: 64px; border-radius: 12px; border: 1px solid var(--border); }
.sl-swatches { display: flex; gap: 1rem; align-items: center; margin: 0.3rem 0 0.6rem; }
.sl-swatches .lbl { color: var(--faint); font-size: 0.78rem; text-align: center; margin-top: 0.3rem; }

.sl-compare { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; }
.sl-compare > div { padding: 0.9rem 1rem; border-radius: 14px; background: rgba(2, 6, 23, 0.35); border: 1px solid var(--border); }
.sl-compare h4 { margin: 0 0 0.35rem; font-size: 1rem; }
.sl-compare p, .sl-compare li { color: var(--muted); font-size: 0.88rem; }

.sl-prose p, .sl-prose li { color: var(--muted); line-height: 1.6; }
.sl-prose b, .sl-prose strong { color: var(--text); }

/* ---------- Rodapé ---------- */
.sl-footer {
  margin-top: 2.2rem; padding: 1.1rem 0 0.4rem; border-top: 1px solid var(--border);
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 0.8rem;
  color: var(--faint); font-size: 0.8rem; line-height: 1.6;
}
.sl-footer b { color: var(--muted); font-weight: 600; }

@keyframes sl-fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

/* ---------- Texto, ficheiros e caracteres invisíveis ---------- */
.sl-textprev {
  font-family: var(--mono); font-size: 0.84rem; line-height: 1.6; color: var(--text);
  white-space: pre-wrap; word-break: break-word; max-height: 260px; overflow: auto;
  padding: 0.9rem 1rem; border-radius: 12px;
  background: rgba(2, 6, 23, 0.5); border: 1px solid var(--border);
}
.sl-zw { display: inline; letter-spacing: 1px; }
.sl-zw i {
  display: inline-block; width: 0.42rem; height: 0.9rem; margin: 0 1px; vertical-align: -2px;
  border-radius: 2px; font-style: normal;
}
.sl-zw i.b0 { background: rgba(56, 189, 248, 0.35); }
.sl-zw i.b1 { background: rgba(56, 189, 248, 0.85); }
.sl-zw i.b2 { background: rgba(52, 211, 153, 0.45); }
.sl-zw i.b3 { background: rgba(52, 211, 153, 0.95); }
.sl-zw .more { color: var(--emerald); font-size: 0.78rem; margin-left: 0.3rem; }
.sl-legend { display: flex; flex-wrap: wrap; gap: 0.8rem; color: var(--faint); font-size: 0.78rem; margin-top: 0.5rem; }
.sl-legend .sl-zw i { margin-right: 0.3rem; }
.sl-filecard {
  display: flex; align-items: center; gap: 1rem; min-height: 130px; padding: 1.1rem 1.2rem;
  border-radius: 12px; border: 1px solid var(--border); background: rgba(2, 6, 23, 0.4);
}
.sl-filecard .ext {
  display: grid; place-items: center; width: 64px; height: 76px; flex: none; border-radius: 10px;
  font-family: var(--mono); font-weight: 700; font-size: 0.85rem; color: #04121F;
  background: linear-gradient(160deg, var(--blue) 0%, var(--emerald) 100%);
  clip-path: polygon(0 0, 72% 0, 100% 22%, 100% 100%, 0 100%);
}
.sl-filecard .name { font-weight: 600; color: var(--text); word-break: break-all; }
.sl-filecard .meta { color: var(--muted); font-size: 0.84rem; margin-top: 0.15rem; }
.sl-code {
  font-family: var(--mono); font-size: 0.78rem; line-height: 1.55; color: #BAE6FD;
  white-space: pre; overflow: auto; max-height: 220px; padding: 0.8rem 1rem; border-radius: 12px;
  background: rgba(2, 6, 23, 0.65); border: 1px solid var(--border);
}

/* ---------- Responsivo ---------- */
@media (max-width: 900px) {
  .sl-flow, .sl-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  [data-testid="stLayoutWrapper"]:has(> .st-key-headerbar) { position: static; }
  .sl-tag { text-align: left; }
  .sl-title { font-size: 1.5rem; }
  .sl-compare { grid-template-columns: 1fr; }
  .sl-flow, .sl-stats { grid-template-columns: 1fr 1fr; }
}
</style>
"""
