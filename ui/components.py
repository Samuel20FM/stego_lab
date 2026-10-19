"""Componentes visuais reutilizáveis (HTML + CSS) para a interface Streamlit.

Todo o texto fornecido pelo utilizador é escapado com ``html.escape`` antes
de ser inserido no HTML.
"""

from __future__ import annotations

import base64
import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as st_components

from .styles import CSS

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FAVICON = ASSETS / "favicon.png"

COURSE = "Segurança Informática"
TEACHER = "Martina de Barros"
MEMBERS = ("Samuel Massinga", "Adilson Chaguala")
INSTITUTION = "Universidade Pedagógica de Maputo · Faculdade de Engenharias e Tecnologias"
YEAR = "2026 · 2.º Semestre"


def fmt_bytes(n: int | float) -> str:
    """1536 -> '1,5 KB' (vírgula decimal, como em Moçambique/Portugal)."""
    units = ["bytes", "KB", "MB", "GB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            text = f"{value:,.0f}" if unit == "bytes" else f"{value:,.1f}"
            return text.replace(",", " ").replace(".", ",") + f" {unit}"
        value /= 1024
    return f"{n} bytes"


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_pct(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + "%"


def inject_css() -> None:
    st.html(CSS)


def brand() -> None:
    """Logótipo, nome e subtítulo (lado esquerdo do cabeçalho)."""
    svg = base64.b64encode((ASSETS / "logo.svg").read_bytes()).decode("ascii")
    st.html(
        f"""
        <div class="sl-brand">
          <img class="sl-logo" src="data:image/svg+xml;base64,{svg}" alt="Logótipo StegoLab">
          <div>
            <h1 class="sl-title">Stego<span>Lab</span></h1>
            <p class="sl-subtitle">Laboratório de Esteganografia - Com LSB</p>
          </div>
        </div>
        """
    )


def header_tag() -> None:
    """Identificação académica discreta (lado direito do cabeçalho)."""
    st.html(
        f'<div class="sl-tag">{" · ".join(reversed(MEMBERS))}<br>'
        f"<b>{COURSE}</b><br>"
        f"Universidade Pedagógica de Maputo<br>{YEAR}</div>"
    )


def scroll_to_top(nonce: int) -> None:
    """Leva o utilizador ao topo da página (usado ao abrir a página de resultado)."""
    st_components.html(
        f"""<script>
        // {nonce}: conteúdo diferente em cada pedido, para o script voltar a correr
        const doc = window.parent.document;
        const targets = [window.parent, doc.querySelector('[data-testid="stMain"]'),
                         doc.querySelector('[data-testid="stAppViewContainer"]'), doc.scrollingElement];
        targets.forEach(t => {{ try {{ t && t.scrollTo({{ top: 0, behavior: "smooth" }}); }} catch (e) {{}} }});
        </script>""",
        height=0,
    )


def footer() -> None:
    st.html(
        f"""
        <footer class="sl-footer">
          <div><b>{COURSE}</b> · Fundamentos de Segurança Informática<br>{INSTITUTION}</div>
          <div><b>Docente:</b> {TEACHER}<br><b>Integrantes:</b> {" e ".join(MEMBERS)}</div>
          <div>Demonstração académica de esteganografia em Python.<br>
        </footer>
        """
    )


def step(num: int | str, title: str, hint: str = "") -> None:
    hint_html = f'<span class="sl-step-hint">{escape(hint)}</span>' if hint else ""
    st.html(
        f'<div class="sl-step"><span class="sl-step-num">{num}</span>'
        f'<span class="sl-step-title">{escape(title)}</span>{hint_html}</div>'
    )


def chips(items: list[tuple[str, str] | tuple[str, str, str]]) -> None:
    parts = []
    for item in items:
        label, value = item[0], item[1]
        cls = item[2] if len(item) > 2 else ""
        parts.append(f'<span class="sl-chip {cls}">{escape(label)} <b>{escape(value)}</b></span>')
    st.html(f'<div class="sl-chips">{"".join(parts)}</div>')


_ICONS = {"success": "✓", "info": "i", "warning": "!", "error": "×"}


def notice(kind: str, title: str, detail: str = "") -> None:
    """Notificação com estado visual: success | info | warning | error."""
    detail_html = f'<div class="d">{escape(detail)}</div>' if detail else ""
    role = "alert" if kind == "error" else "status"
    st.html(
        f'<div class="sl-notice {kind}" role="{role}"><span class="ico">{_ICONS[kind]}</span>'
        f'<div><div class="t">{escape(title)}</div>{detail_html}</div></div>'
    )


def capacity_meter(used: int, total: int, encrypted: bool = False) -> None:
    pct = (used / total * 100) if total else 100.0
    state = "over" if used > total else "warn" if pct >= 85 else ""
    width = min(pct, 100)
    st.html(
        f"""
        <div class="sl-meter {state}" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{width:.0f}">
          <div class="sl-meter-top"><span>Ocupação estimada do ficheiro</span>
            <span><b>{fmt_bytes(used)}</b> de <b>{fmt_bytes(total)}</b> · <b>{fmt_pct(pct)}</b></span></div>
          <div class="sl-meter-track"><div class="sl-meter-fill" style="width:{width:.2f}%"></div></div>
          <div class="sl-meter-foot">Inclui o cabeçalho de 14 bytes{" e a sobrecarga da encriptação (sal + token Fernet)" if encrypted else ""}.</div>
        </div>
        """
    )


def counter(chars: int, nbytes: int) -> None:
    st.html(
        f'<div class="sl-counter"><span><b>{fmt_int(chars)}</b> caracteres</span>'
        f'<span><b>{fmt_int(nbytes)}</b> bytes em UTF-8</span></div>'
    )


def empty_preview(text: str) -> None:
    st.html(
        f"""<div class="sl-empty"><div>
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/></svg>
        <div>{escape(text)}</div></div></div>"""
    )


def stats(items: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="sl-stat"><div class="k">{escape(k)}</div><div class="v">{escape(v)}</div></div>'
        for k, v in items
    )
    st.html(f'<div class="sl-stats">{cells}</div>')


def text_preview(text: str, limit: int = 1500) -> None:
    more = "…" if len(text) > limit else ""
    st.html(f'<div class="sl-textprev">{escape(text[:limit])}{more}</div>')


ZW_CHARS = ("\u200b", "\u200c", "\u200d", "\u2060")


def zero_width_view(text: str, start: int, end: int, max_marks: int = 320) -> None:
    """Mostra o texto com os caracteres invisíveis desenhados como blocos coloridos."""
    marks = "".join(
        f'<i class="b{ZW_CHARS.index(c)}" title="U+{ord(c):04X}"></i>'
        for c in text[start : min(end, start + max_marks)]
    )
    hidden = end - start - max_marks
    more = f'<span class="more">… mais {fmt_int(hidden)} caracteres invisíveis</span>' if hidden > 0 else ""
    before = text[max(0, start - 120) : start]
    after = text[end : end + 240]
    legend = "".join(
        f'<span><span class="sl-zw"><i class="b{i}"></i></span>U+{ord(c):04X} = {i:02b}</span>'
        for i, c in enumerate(ZW_CHARS)
    )
    st.html(
        f'<div class="sl-textprev">{"…" if start > 120 else ""}{escape(before)}'
        f'<span class="sl-zw">{marks}{more}</span>{escape(after)}{"…" if len(text) > end + 240 else ""}</div>'
        f'<div class="sl-legend">{legend}</div>'
    )


def file_card(ext: str, name: str, meta: str) -> None:
    st.html(
        f'<div class="sl-filecard"><div class="ext">{escape(ext.upper()[:5])}</div>'
        f'<div><div class="name">{escape(name)}</div><div class="meta">{escape(meta)}</div></div></div>'
    )


def code_view(text: str) -> None:
    st.html(f'<div class="sl-code">{escape(text)}</div>')


def secret_box(message: str) -> None:
    st.html(f'<div class="sl-secret" aria-label="Mensagem recuperada">{escape(message)}</div>')


def copy_button(text: str, key: str) -> None:
    """Botão "Copiar" que usa a área de transferência do navegador."""
    payload = json.dumps(text).replace("</", "<\\/")
    st_components.html(
        f"""
        <style>
          body {{ margin: 0; background: transparent; font-family: Inter, "Segoe UI", Roboto, sans-serif; }}
          button {{
            display: inline-flex; align-items: center; gap: .45rem; cursor: pointer;
            padding: .5rem .95rem; border-radius: 11px; font-weight: 600; font-size: .9rem;
            color: #E2E8F0; background: rgba(148,163,184,.08); border: 1px solid rgba(148,163,184,.28);
            transition: transform .15s ease, border-color .2s ease, background .2s ease;
          }}
          button:hover {{ transform: translateY(-1px); border-color: #38BDF8; background: rgba(56,189,248,.1); }}
          button.ok {{ border-color: #34D399; color: #34D399; }}
        </style>
        <button id="b-{key}" type="button" aria-live="polite">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <span>Copiar mensagem</span>
        </button>
        <script>
          const text = {payload};
          const btn = document.getElementById("b-{key}");
          function done(ok) {{
            btn.classList.toggle("ok", ok);
            btn.querySelector("span").textContent = ok ? "Copiado!" : "Seleccione e copie manualmente";
            setTimeout(() => {{ btn.classList.remove("ok"); btn.querySelector("span").textContent = "Copiar mensagem"; }}, 2200);
          }}
          function fallback() {{
            const ta = document.createElement("textarea");
            ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
            document.body.appendChild(ta); ta.select();
            let ok = false; try {{ ok = document.execCommand("copy"); }} catch (e) {{}}
            ta.remove(); done(ok);
          }}
          btn.addEventListener("click", () => {{
            if (navigator.clipboard && window.isSecureContext) {{
              navigator.clipboard.writeText(text).then(() => done(true), fallback);
            }} else {{ fallback(); }}
          }});
        </script>
        """,
        height=46,
    )
