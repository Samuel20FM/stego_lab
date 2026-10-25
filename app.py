"""StegoLab — Laboratório de Esteganografia (interface Streamlit).

Executar:  streamlit run app.py

A lógica de esteganografia vive no pacote ``steganography`` e não depende do
Streamlit; este ficheiro apenas trata da interface.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
import time
import wave
from datetime import date, datetime, timedelta
from datetime import time as dtime
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image, ImageChops

from steganography import (
    COVER_TYPES,
    MAX_MESSAGE_BYTES,
    MAX_SECRET_FILE_BYTES,
    OUTPUT_FORMATS,
    CorruptPayloadError,
    ExpiredMessageError,
    NoPayloadError,
    Secret,
    StegoError,
    WrongPasswordError,
    estimate_size,
    format_datetime,
    hide,
    max_secret_file,
    open_carrier,
    reveal,
)
from steganography.carriers import VIDEO_MAX_BYTES
from steganography.payload import HEADER_SIZE
from ui import components as ui

st.set_page_config(
    page_title="StegoLab — Laboratório de Esteganografia",
    page_icon=str(ui.FAVICON),
    layout="wide",
    initial_sidebar_state="collapsed",
)

FORMAT_LABELS = {
    "PNG": "PNG (recomendado)",
    "BMP": "BMP",
    "TIFF": "TIFF",
    "WEBP": "WebP sem perdas",
}
VALIDITY = {
    "Sem limite": None,
    "1 hora": 3600,
    "24 horas": 24 * 3600,
    "7 dias": 7 * 24 * 3600,
    "Personalizada": 0,
}
SHARE_TIPS = {
    "image": "Redimensionar, recortar, editar ou comprimir (JPEG, WhatsApp, redes sociais) destrói a mensagem.",
    "audio": "Não converta para MP3/AAC nem edite o áudio: a compressão com perdas destrói a mensagem.",
    "video": "Envie o .mkv tal como está. Converter para MP4 ou partilhar em redes sociais recomprime o áudio e destrói a mensagem.",
    "text": "Envie o próprio ficheiro. Copiar e colar em algumas aplicações remove os caracteres invisíveis.",
    "pdf": "Não volte a gravar nem a “optimizar” o PDF noutro programa: os comentários podem ser removidos.",
    "zip": "Não abra e grave o documento de novo no Word/LibreOffice: o comentário do ZIP é descartado.",
}


# --------------------------------------------------------------------------
# Utilitários de estado e de ficheiros
# --------------------------------------------------------------------------

def _state_defaults() -> None:
    st.session_state.setdefault("hide_nonce", 0)
    st.session_state.setdefault("extract_nonce", 0)
    st.session_state.setdefault("view", "lab")  # "lab" | "result"
    st.session_state.setdefault("scroll_nonce", 0)


def _go_result() -> None:
    st.session_state.view = "result"
    st.session_state.scroll_nonce += 1


def _go_lab() -> None:
    st.session_state.view = "lab"
    st.session_state.scroll_nonce += 1


def _new_hide() -> None:
    _reset_hide()
    _go_lab()


def _reset_hide() -> None:
    st.session_state.hide_nonce += 1
    st.session_state.pop("hide_result", None)


def _reset_extract() -> None:
    st.session_state.extract_nonce += 1
    st.session_state.pop("extract_result", None)


@st.cache_resource(show_spinner=False, max_entries=8)
def _open(data: bytes, name: str):
    """Valida o ficheiro carregado (pelo conteúdo, não pela extensão)."""
    return open_carrier(data, name)


def _digest(*parts: bytes | str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part if isinstance(part, bytes) else part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _plays_in_browser(carrier) -> bool:
    return carrier.demuxer == "mov" or b"webm" in carrier.data[:64]


def _preview(carrier, name: str) -> None:
    kind = carrier.kind
    if kind == "image":
        st.image(carrier.image, width="stretch", caption=name)
    elif kind == "audio":
        ui.file_card("wav", name, f"{carrier.label} · {ui.fmt_bytes(carrier.size)}")
        st.audio(carrier.data, format="audio/wav")
    elif kind == "video":
        if _plays_in_browser(carrier):
            st.video(carrier.data, format="video/webm" if carrier.demuxer == "matroska" else "video/mp4")
        else:
            st.image(carrier.first_frame, width="stretch", caption=f"{name} · primeiro fotograma")
    elif kind == "text":
        ui.text_preview(carrier.text)
    else:
        ext = Path(name).suffix.lstrip(".") or getattr(carrier, "ext", kind)
        ui.file_card(ext, name, f"{carrier.label} · {ui.fmt_bytes(carrier.size)}")
    ui.chips(carrier.details() + [("Tamanho", ui.fmt_bytes(carrier.size))])


def _cover_notes(carrier) -> None:
    kind = carrier.kind
    if kind == "image" and carrier.lossy:
        ui.notice(
            "info",
            "Imagem JPEG aceite como ponto de partida",
            "O resultado será gravado num formato sem perdas (PNG por omissão). "
            "Nunca volte a converter a imagem final para JPEG.",
        )
    elif kind == "video":
        ui.notice(
            "info",
            "O vídeo não é recodificado",
            "O segredo vai para a faixa de áudio, convertida em PCM sem perdas. O resultado é um "
            f"ficheiro .mkv (abre no VLC) com cerca de {ui.fmt_bytes(carrier.estimated_output)}.",
        )
    elif kind == "text":
        ui.notice(
            "info",
            "Caracteres invisíveis",
            "O texto visível fica igual. Algumas aplicações (redes sociais, certos editores) "
            "removem estes caracteres e, com eles, a mensagem.",
        )
    elif kind == "pdf":
        ui.notice(
            "info",
            "Ocultação na estrutura do PDF (não é LSB)",
            "O PDF abre e imprime como antes, mas quem o abrir num editor de texto vê o bloco "
            "escondido. Use palavra-passe para proteger o conteúdo.",
        )
    elif kind == "zip":
        ui.notice(
            "info",
            "Comentário do arquivo ZIP (até 64 KB)",
            "O documento abre normalmente. Se for gravado de novo no Word ou no LibreOffice, "
            "o comentário — e o segredo — desaparecem.",
        )


def _out_ext(carrier) -> str:
    return {"audio": "wav", "video": "mkv", "pdf": "pdf"}.get(carrier.kind) or getattr(carrier, "ext", "")


ZOOM_W, ZOOM_H, ZOOM_SCALE = 40, 20, 12


def _diff_map(original: Image.Image, stego: Image.Image) -> tuple[Image.Image, int, int]:
    """Zoom do canto superior esquerdo com os píxeis alterados a verde.

    Devolve também o número de píxeis e de canais de cor efectivamente alterados
    (cerca de metade dos bits escritos já tinham o valor certo).
    """
    a, b = original.convert("RGB"), stego.convert("RGB")
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()  # 3 x 256 posições (R, G, B)
    changed_channels = sum(sum(hist[c * 256 + 1 : c * 256 + 256]) for c in range(3))

    r, g, bl = diff.point(lambda v: 255 if v else 0).split()
    mask = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    changed_pixels = mask.histogram()[255]

    box = (0, 0, min(ZOOM_W, a.width), min(ZOOM_H, a.height))
    zoom = Image.blend(a.crop(box), Image.new("RGB", (box[2], box[3]), (10, 16, 32)), 0.6)
    zoom.paste((52, 211, 153), mask=mask.crop(box))
    zoom = zoom.resize((box[2] * ZOOM_SCALE, box[3] * ZOOM_SCALE), Image.NEAREST)
    return zoom, changed_pixels, changed_channels


def _pcm_to_wav(carrier, seconds: int = 30) -> bytes:
    """Primeiros segundos da faixa de áudio (PCM 16 bits) de um vídeo, como WAV."""
    pcm = carrier._pcm[: seconds * carrier.sample_rate * carrier.channels * 2]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(carrier.channels)
        w.setsampwidth(2)
        w.setframerate(carrier.sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _visuals(orig, stego, out, payload_bytes: int) -> dict:
    """Dados para a página de resultado, consoante o tipo de portador."""
    kind = orig.kind
    if kind == "image":
        diff, px, ch = _diff_map(orig.image, stego.image)
        mode = "RGBA" if "A" in orig.image.mode else "RGB"
        return {"original": orig.image.convert(mode), "stego": stego.image,
                "diff": diff, "changed_px": px, "changed_ch": ch}
    if kind in ("audio", "video"):
        n = payload_bytes * 8  # só esta zona foi escrita
        changed = sum(1 for x, y in zip(orig.slots()[:n], stego.slots()[:n]) if x != y)
        res = {"changed": changed, "slots": len(orig.slots())}
        if kind == "audio":
            res.update(src_audio=orig.data, audio=out.data)
        else:
            res.update(frame=orig.first_frame, audio=_pcm_to_wav(stego))
        return res
    if kind == "text":
        return {"text": stego.text, "run": stego.payload_run()}
    if kind == "pdf":
        m = re.search(rb"%STGL-BEGIN.*?%STGL-END", out.data, re.S)
        lines = m.group().decode("ascii").splitlines() if m else []
        if len(lines) > 8:
            lines = lines[:5] + [f"… ({len(lines) - 7} linhas omitidas)"] + lines[-2:]
        return {"snippet": "\n".join(lines + ["startxref"])}
    if kind == "zip":
        comment = stego.comment[:64]
        rows = [
            f"{i:04X}  {' '.join(f'{b:02X}' for b in comment[i:i + 16]):<47}  "
            + "".join(chr(b) if 32 <= b < 127 else "." for b in comment[i : i + 16])
            for i in range(0, len(comment), 16)
        ]
        return {"snippet": "\n".join(rows) + ("\n…" if len(stego.comment) > 64 else "")}
    return {}


def _show_error(exc: Exception) -> None:
    if isinstance(exc, StegoError):
        ui.notice("error", "Não foi possível concluir a operação", str(exc))
    else:  # erro inesperado: mensagem genérica, sem stack trace
        ui.notice(
            "error",
            "Ocorreu um erro inesperado",
            "Verifique o ficheiro e tente novamente. Se o problema persistir, reinicie a aplicação.",
        )


# --------------------------------------------------------------------------
# Separador 1 — Esconder
# --------------------------------------------------------------------------

def render_hide_tab() -> None:
    nonce = st.session_state.hide_nonce
    left, right = st.columns([1, 1.15], gap="large")

    carrier = None
    cap = 0
    data = b""
    with left:
        with st.container(key="card_hide_image"):
            ui.step(1, "Ficheiro de cobertura", "Imagem · WAV · Vídeo · Texto · PDF · Office")
            upload = st.file_uploader(
                "Carregar ficheiro de cobertura",
                type=COVER_TYPES,
                key=f"hide_upload_{nonce}",
                help="O tipo é detectado pelo conteúdo, não pela extensão. O ficheiro original nunca é alterado.",
                label_visibility="collapsed",
            )
            if upload is None:
                ui.empty_preview(
                    "Carregue uma imagem, um áudio WAV, um vídeo, um texto, um PDF ou um documento Office."
                )
            else:
                data = upload.getvalue()
                try:
                    with st.spinner("A analisar o ficheiro…"):
                        carrier = _open(data, upload.name)
                        cap = carrier.capacity()
                except Exception as exc:
                    _show_error(exc)
                    carrier = None
                if carrier is not None:
                    _preview(carrier, upload.name)
                    ui.chips(
                        [
                            ("Capacidade" if carrier.lsb else "Limite", ui.fmt_bytes(cap), "ok"),
                            ("Técnica", carrier.technique),
                        ]
                    )
                    _cover_notes(carrier)

    with right:
        with st.container(key="card_hide_message"):
            ui.step(2, "Segredo", "Texto ou ficheiro")
            mode = st.segmented_control(
                "Tipo de segredo",
                options=["Texto", "Ficheiro"],
                format_func=lambda o: {"Texto": "Mensagem de texto", "Ficheiro": "Ficheiro"}[o],
                default="Texto",
                required=True,
                key=f"hide_kind_{nonce}",
                label_visibility="collapsed",
            ) or "Texto"

            message = ""
            secret_data = b""
            secret_name = None
            if mode == "Texto":
                message = st.text_area(
                    "Mensagem secreta",
                    key=f"hide_message_{nonce}",
                    height=170,
                    placeholder="Escreva aqui a mensagem a esconder… (acentos e emojis são suportados)",
                    label_visibility="collapsed",
                    help="Ctrl+Enter actualiza o contador e a capacidade.",
                ) or ""
                content_len = len(message.encode("utf-8"))
                ui.counter(len(message), content_len)
            else:
                # O limite depende do ficheiro de cobertura, não do limite geral de upload.
                plain_max = max_secret_file(cap) if carrier is not None else MAX_SECRET_FILE_BYTES
                secret_upload = st.file_uploader(
                    "Ficheiro a esconder",
                    key=f"hide_secret_{nonce}",
                    help="Qualquer tipo de ficheiro (PDF, ZIP, imagem…). O StegoLab nunca o abre nem o executa.",
                    max_upload_size=max(1, math.ceil(plain_max / (1024 * 1024))),
                    label_visibility="collapsed",
                )
                if carrier is None:
                    st.caption(
                        "Carregue primeiro o ficheiro de cobertura: é ele que define o tamanho máximo "
                        f"do segredo (nunca mais de {ui.fmt_bytes(MAX_SECRET_FILE_BYTES)})."
                    )
                elif secret_upload is None:
                    st.caption(
                        f"Este ficheiro de cobertura aguenta um segredo até **{ui.fmt_bytes(plain_max)}** "
                        f"(**{ui.fmt_bytes(max_secret_file(cap, encrypted=True))}** com palavra-passe). "
                        "O nome do ficheiro também ocupa espaço."
                    )
                else:
                    secret_data = secret_upload.getvalue()
                    secret_name = secret_upload.name
                    ui.chips([("Ficheiro", secret_name), ("Tamanho", ui.fmt_bytes(len(secret_data)))])
                content_len = len(secret_data)

            encrypt = st.toggle(
                "Proteger o conteúdo com palavra-passe (encriptação Fernet)",
                key=f"hide_encrypt_{nonce}",
                help="Opcional. O segredo é encriptado antes de ser escondido.",
            )
            password = confirm = ""
            if encrypt:
                c1, c2 = st.columns(2)
                # live=True envia o valor ao servidor enquanto se escreve. Sem isto, o valor
                # só chega no blur/Enter, e um clique imediato no botão via o campo vazio.
                password = c1.text_input(
                    "Palavra-passe", type="password", key=f"hide_pw_{nonce}",
                    live=True, autocomplete="new-password",
                )
                confirm = c2.text_input(
                    "Confirmar palavra-passe", type="password", key=f"hide_pw2_{nonce}",
                    live=True, autocomplete="new-password",
                )

            validity = st.segmented_control(
                "Validade do segredo",
                options=list(VALIDITY),
                default="Sem limite",
                required=True,
                key=f"hide_validity_{nonce}",
                help="Depois desta data, o StegoLab recusa revelar o segredo.",
            ) or "Sem limite"
            custom_ts = None
            if validity == "Personalizada":
                c1, c2 = st.columns(2)
                day = c1.date_input(
                    "Data", value=date.today() + timedelta(days=1), min_value=date.today(),
                    format="DD/MM/YYYY", key=f"hide_date_{nonce}",
                )
                hour = c2.time_input("Hora", value=dtime(12, 0), key=f"hide_time_{nonce}")
                custom_ts = int(datetime.combine(day, hour).timestamp())
            expires = validity != "Sem limite"
            if expires and not encrypt:
                ui.notice(
                    "info",
                    "Proteja a validade com palavra-passe",
                    "Sem encriptação, quem conhecer o formato pode alterar a data. Com palavra-passe, "
                    "a data fica dentro da cifra e é autenticada (HMAC).",
                )

            fmt = None
            if carrier is not None and carrier.output_formats:
                fmt = st.segmented_control(
                    "Formato do ficheiro de saída",
                    options=list(OUTPUT_FORMATS),
                    format_func=FORMAT_LABELS.get,
                    default="PNG",
                    required=True,
                    key=f"hide_fmt_{nonce}",
                    help="Apenas formatos sem perdas. JPEG não é oferecido: a compressão destrói os bits escondidos.",
                ) or "PNG"
            elif carrier is not None:
                st.caption(f"Ficheiro de saída: **.{_out_ext(carrier)}** (o tipo do original é mantido sempre que possível).")

            # ---- Capacidade e validação antes de permitir a codificação ----
            problems: list[str] = []
            if carrier is not None:
                total = cap + HEADER_SIZE
                used = (
                    estimate_size(content_len, filename=secret_name, expires=expires, encrypted=encrypt)
                    if content_len
                    else HEADER_SIZE
                )
                ui.capacity_meter(used, total, encrypted=encrypt)
                if used > total:
                    problems.append(
                        f"O segredo ultrapassa a capacidade do ficheiro em {ui.fmt_bytes(used - total)}. "
                        "Use um ficheiro de cobertura maior ou um segredo mais pequeno."
                    )
                if carrier.kind == "video" and carrier.estimated_output > VIDEO_MAX_BYTES:
                    problems.append("O vídeo resultante excederia 100 MB. Use um vídeo mais curto.")
            if mode == "Texto" and content_len > MAX_MESSAGE_BYTES:
                problems.append(f"O limite da aplicação é {ui.fmt_int(MAX_MESSAGE_BYTES)} bytes por mensagem.")
            if mode == "Ficheiro" and content_len > MAX_SECRET_FILE_BYTES:
                problems.append(f"O ficheiro a esconder excede o limite de {ui.fmt_bytes(MAX_SECRET_FILE_BYTES)}.")
            if custom_ts is not None and custom_ts <= time.time():
                problems.append("A data de validade tem de ser no futuro.")
            if encrypt and password and confirm and password != confirm:
                problems.append("As palavras-passe não coincidem.")
            if encrypt and password and len(password) < 4:
                problems.append("Use uma palavra-passe com pelo menos 4 caracteres.")
            for p in problems:
                ui.notice("warning", "Atenção", p)

            # O botão fica activo assim que existe ficheiro: o Streamlit só confirma
            # o texto ao sair do campo, por isso a validação final é feita no clique.
            b1, b2 = st.columns([2, 1])
            go = b1.button(
                "Esconder segredo",
                type="primary",
                icon=":material/visibility_off:",
                width="stretch",
                disabled=carrier is None,
                key=f"hide_go_{nonce}",
            )
            b2.button(
                "Limpar",
                icon=":material/restart_alt:",
                width="stretch",
                on_click=_reset_hide,
                key=f"hide_clear_{nonce}",
            )
            if carrier is None:
                st.caption("Carregue um ficheiro de cobertura para começar.")

            error = None
            if go:
                if mode == "Texto" and not message.strip():
                    error = "Escreva uma mensagem antes de a esconder."
                elif mode == "Ficheiro" and not secret_data:
                    error = "Escolha o ficheiro a esconder."
                elif problems:
                    error = problems[0]
                elif encrypt and not password:
                    error = "Introduza uma palavra-passe ou desactive a encriptação."
                elif encrypt and not confirm:
                    error = "Repita a palavra-passe no campo «Confirmar palavra-passe»."
                elif encrypt and password != confirm:
                    error = "Confirme a palavra-passe: os dois campos têm de ser iguais."
                if error:
                    ui.notice("error", "Não é possível esconder o segredo", error)

    signature = _digest(
        data, mode, message, secret_data, secret_name or "", fmt or "",
        "enc" if encrypt else "plain", validity, str(custom_ts),
    )

    if go and carrier is not None and error is None:
        try:
            with st.spinner("A esconder o segredo…"):
                if validity == "Personalizada":
                    expires_at = custom_ts
                else:
                    expires_at = int(time.time()) + VALIDITY[validity] if expires else None
                secret = (
                    Secret.text(message, expires_at)
                    if mode == "Texto"
                    else Secret.file(secret_name, secret_data, expires_at)
                )
                pw = password if encrypt else None
                out = hide(carrier, secret, pw, fmt)
                # Autoverificação: reabre o ficheiro gerado e extrai o segredo.
                check = open_carrier(out.data, f"{carrier.stem}.{out.ext}")
                verified = reveal(check, password=pw).secret == secret
                payload_bytes = estimate_size(
                    len(secret.content), filename=secret.filename, expires=expires, encrypted=encrypt
                )
                visuals = _visuals(carrier, check, out, payload_bytes)
            st.session_state.hide_result = {
                "signature": signature,
                "kind": carrier.kind,
                "label": carrier.label,
                "technique": carrier.technique,
                "bytes": out.data,
                "ext": out.ext,
                "filename": f"{carrier.stem}_stego.{out.ext}",
                "mime": out.mime,
                "payload": payload_bytes,
                "pct": payload_bytes / (cap + HEADER_SIZE) * 100,
                "encrypted": encrypt,
                "verified": verified,
                "expires_at": expires_at,
                "secret_desc": (
                    f"texto · {ui.fmt_bytes(len(secret.content))}"
                    if mode == "Texto"
                    else f"{secret.filename} · {ui.fmt_bytes(len(secret.content))}"
                ),
                "src_name": upload.name,
                "src_size": carrier.size,
                "src_format": getattr(getattr(carrier, "info", None), "format", carrier.label),
                **visuals,
            }
        except Exception as exc:
            st.session_state.pop("hide_result", None)
            _show_error(exc)
        else:
            # Leva o utilizador directamente para a página de resultado.
            _go_result()
            st.rerun()

    result = st.session_state.get("hide_result")
    if result and result["signature"] == signature:
        ui.notice(
            "success",
            "Resultado pronto",
            "Use o botão “Ver resultado” no topo da página para ver a comparação e descarregar o ficheiro.",
        )


def _result_stats(r: dict) -> list[tuple[str, str]]:
    kind, pct = r["kind"], ui.fmt_pct(r["pct"])
    bits = ui.fmt_int(r["payload"] * 8)
    if kind == "image":
        return [("Bits escritos", bits), ("Canais alterados", ui.fmt_int(r["changed_ch"])),
                ("Píxeis alterados", ui.fmt_int(r["changed_px"])), ("Capacidade usada", pct)]
    if kind in ("audio", "video"):
        return [("Bits escritos", bits), ("Amostras alteradas", ui.fmt_int(r["changed"])),
                ("Amostras disponíveis", ui.fmt_int(r["slots"])), ("Capacidade usada", pct)]
    size_change = f"{ui.fmt_bytes(r['src_size'])} → {ui.fmt_bytes(len(r['bytes']))}"
    if kind == "text":
        return [("Bytes escondidos", ui.fmt_int(r["payload"])),
                ("Caracteres invisíveis", ui.fmt_int(r["payload"] * 4)),
                ("Tamanho do ficheiro", size_change), ("Limite usado", pct)]
    return [("Bytes escondidos", ui.fmt_int(r["payload"])), ("Tamanho do ficheiro", size_change),
            ("Técnica", "estrutural"), ("Limite usado", pct)]


def _result_visuals(r: dict) -> None:
    kind = r["kind"]
    if kind == "image":
        c1, c2, c3 = st.columns(3, gap="medium")
        c1.image(r["original"], width="stretch", caption=f"Original · {r['src_format']} · {ui.fmt_bytes(r['src_size'])}")
        c2.image(r["stego"], width="stretch", caption=f"Com mensagem · {r['ext'].upper()} · {ui.fmt_bytes(len(r['bytes']))}")
        c3.image(r["diff"], width="stretch", caption=f"Zoom ×{ZOOM_SCALE} no canto superior esquerdo ({ZOOM_W}×{ZOOM_H} píxeis): a verde, os píxeis alterados")
        st.caption(
            "As duas imagens são visualmente idênticas: cada canal muda no máximo 1 unidade em 255. "
            "Os bits são escritos linha a linha a partir do canto superior esquerdo; cerca de metade "
            "já tinha o valor certo, por isso há menos canais alterados do que bits escritos."
        )
    elif kind == "audio":
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("**Original**")
            st.audio(r["src_audio"], format="audio/wav")
        with c2:
            st.markdown("**Com o segredo**")
            st.audio(r["audio"], format="audio/wav")
        st.caption(
            "Cada amostra muda no máximo 1 unidade (em 65 536, num WAV de 16 bits): a diferença é inaudível. "
            "Cerca de metade das amostras usadas já tinha o bit certo."
        )
    elif kind == "video":
        c1, c2 = st.columns(2, gap="medium")
        c1.image(r["frame"], width="stretch", caption="Primeiro fotograma: o fluxo de vídeo é copiado sem recodificação")
        with c2:
            st.markdown("**Faixa de áudio com o segredo** (primeiros 30 s, PCM 16 bits)")
            st.audio(r["audio"], format="audio/wav")
            st.caption(
                "O ficheiro .mkv abre no VLC ou no mpv; alguns navegadores não o reproduzem. "
                "Cada amostra muda no máximo 1 unidade em 65 536."
            )
    elif kind == "text":
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("**Como o destinatário vê o texto**")
            ui.text_preview(r["text"])
        with c2:
            st.markdown("**Com os caracteres invisíveis à vista**")
            start, end = r["run"]
            ui.zero_width_view(r["text"], start, end)
    else:
        where = (
            "Linhas inseridas antes de startxref: em PDF, “%” inicia um comentário que os leitores ignoram."
            if kind == "pdf"
            else "Comentário no fim do arquivo ZIP (hexadecimal): começa pelo identificador STGL."
        )
        st.markdown(f"**{where}**")
        ui.code_view(r["snippet"])


def render_result_page() -> None:
    """Página dedicada ao resultado da operação "Esconder"."""
    r = st.session_state.hide_result
    with st.container(key="cardresult_hide"):
        ui.step("✓", "Resultado", f"{r['label']} de partida: {r['src_name']} · o original não foi alterado")
        if r["verified"]:
            ui.notice(
                "success",
                "Segredo escondido com sucesso",
                "O ficheiro gerado foi reaberto e o segredo foi extraído de novo para confirmar a integridade."
                + (" O conteúdo está encriptado." if r["encrypted"] else ""),
            )
        else:
            ui.notice("warning", "A verificação automática falhou", "Tente novamente ou escolha outro formato de saída.")

        chips = [("Segredo", r["secret_desc"]), ("Técnica", r["technique"])]
        if r["encrypted"]:
            chips.append(("Encriptado", "sim", "lock"))
        if r["expires_at"]:
            chips.append(("Válido até", format_datetime(r["expires_at"]), "lock"))
        ui.chips(chips)
        ui.stats(_result_stats(r))
        _result_visuals(r)

        d1, d2 = st.columns([2, 3])
        d1.download_button(
            f"Descarregar {r['ext'].upper()}",
            data=r["bytes"],
            file_name=r["filename"],
            mime=r["mime"],
            type="primary",
            icon=":material/download:",
            width="stretch",
            on_click="ignore",
        )
        with d2:
            ui.notice("info", "Partilhe o ficheiro sem o editar", SHARE_TIPS[r["kind"]])

    n1, n2, _ = st.columns([1, 1, 1.4])
    n1.button("Voltar e editar", icon=":material/edit:", width="stretch", on_click=_go_lab, key="result_back")
    n2.button("Esconder outro segredo", icon=":material/add:", width="stretch", on_click=_new_hide, key="result_new")


# --------------------------------------------------------------------------
# Separador 2 — Extrair
# --------------------------------------------------------------------------

def render_extract_tab() -> None:
    nonce = st.session_state.extract_nonce
    left, right = st.columns([1, 1.15], gap="large")

    carrier = header = None
    data = b""
    with left:
        with st.container(key="card_extract_image"):
            ui.step(1, "Ficheiro com segredo", "Ficheiro gerado pelo StegoLab")
            upload = st.file_uploader(
                "Carregar ficheiro com segredo",
                type=COVER_TYPES,
                key=f"extract_upload_{nonce}",
                label_visibility="collapsed",
            )
            if upload is None:
                ui.empty_preview("Carregue o ficheiro que contém o segredo escondido.")
            else:
                data = upload.getvalue()
                try:
                    with st.spinner("A analisar o ficheiro…"):
                        carrier = _open(data, upload.name)
                except Exception as exc:
                    _show_error(exc)
                if carrier is not None:
                    _preview(carrier, upload.name)

    with right:
        with st.container(key="card_extract_result"):
            ui.step(2, "Recuperar o segredo")
            password = ""
            if carrier is None:
                ui.empty_preview("A análise do cabeçalho aparece aqui.")
            else:
                try:
                    with st.spinner("A procurar o cabeçalho STGL…"):
                        header = carrier.read_header()
                except NoPayloadError:
                    ui.notice(
                        "error",
                        "Nenhum segredo StegoLab encontrado",
                        "O identificador “STGL” não está presente. O ficheiro pode não ter segredo, "
                        "ou ter sido convertido, editado ou comprimido.",
                    )
                except CorruptPayloadError as exc:
                    ui.notice("error", "Cabeçalho encontrado, mas inválido", str(exc))
                except Exception as exc:
                    _show_error(exc)

                if carrier.kind == "image" and carrier.lossy and header is None:
                    ui.notice(
                        "warning",
                        "Ficheiro JPEG",
                        "A compressão JPEG altera os bits menos significativos; mensagens escondidas não sobrevivem.",
                    )

                if header is not None:
                    ui.chips(
                        [
                            ("Identificador", "STGL ✓", "ok"),
                            ("Técnica", carrier.technique),
                            ("Dados", ui.fmt_bytes(header.length)),
                            ("Encriptado", "sim" if header.encrypted else "não", "lock" if header.encrypted else ""),
                        ]
                    )
                    if header.encrypted:
                        password = st.text_input(
                            "Palavra-passe",
                            type="password",
                            key=f"extract_pw_{nonce}",
                            live=True,
                            help="Este segredo foi protegido com encriptação Fernet.",
                        )

            b1, b2 = st.columns([2, 1])
            go = b1.button(
                "Extrair segredo",
                type="primary",
                icon=":material/visibility:",
                width="stretch",
                disabled=header is None,
                key=f"extract_go_{nonce}",
            )
            b2.button(
                "Limpar",
                icon=":material/restart_alt:",
                width="stretch",
                on_click=_reset_extract,
                key=f"extract_clear_{nonce}",
            )

            signature = _digest(data)
            if go and header is not None:
                try:
                    with st.spinner("A ler o segredo…"):
                        res = reveal(carrier, password=password or None)
                    st.session_state.extract_result = {
                        "signature": signature,
                        "secret": res.secret,
                        "encrypted": res.encrypted,
                        "bytes": res.data_bytes,
                    }
                except WrongPasswordError as exc:
                    st.session_state.pop("extract_result", None)
                    ui.notice("error", "Palavra-passe incorrecta", str(exc))
                except ExpiredMessageError as exc:
                    st.session_state.pop("extract_result", None)
                    ui.notice("error", "Segredo expirado", str(exc))
                except Exception as exc:
                    st.session_state.pop("extract_result", None)
                    _show_error(exc)

            result = st.session_state.get("extract_result")
            if result and result["signature"] == signature:
                _render_revealed(result, nonce)


def _render_revealed(result: dict, nonce: int) -> None:
    secret = result["secret"]
    extra = " · desencriptado com sucesso" if result["encrypted"] else ""
    if secret.expires_at:
        extra += f" · válido até {format_datetime(secret.expires_at)}"
    if secret.is_file:
        ui.notice(
            "success",
            "Ficheiro recuperado",
            f"{ui.fmt_bytes(len(secret.content))} · {ui.fmt_bytes(result['bytes'])} lidos{extra}",
        )
        ext = Path(secret.filename).suffix.lstrip(".") or "bin"
        ui.file_card(ext, secret.filename, ui.fmt_bytes(len(secret.content)))
        st.download_button(
            f"Descarregar {secret.filename}",
            data=secret.content,
            file_name=secret.filename,
            mime="application/octet-stream",
            type="primary",
            icon=":material/download:",
            on_click="ignore",
        )
        st.caption("O StegoLab não abre nem executa o ficheiro. Abra-o apenas se confiar na origem.")
        return

    message = secret.message
    ui.notice(
        "success",
        "Mensagem recuperada",
        f"{ui.fmt_int(len(message))} caracteres · {ui.fmt_bytes(result['bytes'])} lidos{extra}",
    )
    ui.secret_box(message)
    c1, c2 = st.columns(2)
    with c1:
        ui.copy_button(message, key=f"copy{nonce}")
    c2.download_button(
        "Guardar como .txt",
        data=message.encode("utf-8"),
        file_name="mensagem_recuperada.txt",
        mime="text/plain",
        icon=":material/description:",
        on_click="ignore",
    )


# --------------------------------------------------------------------------
# Separador 3 — Como funciona?
# --------------------------------------------------------------------------

def _bits_html(value: int, changed: bool = False) -> str:
    b = f"{value:08b}"
    cls = "lsb changed" if changed else "lsb"
    return f'<span class="sl-bits"><span class="hi">{b[:7]}</span><span class="{cls}">{b[7]}</span></span>'


def render_how_tab() -> None:
    with st.container(key="card_how_intro"):
        st.markdown("#### Esteganografia LSB em quatro passos")
        st.html(
            """
            <div class="sl-flow">
              <div class="sl-flow-step"><div class="n">01 · TEXTO → BYTES</div><div class="h">Codificação UTF-8</div>
                <div class="p">A mensagem é convertida em bytes UTF-8, o que suporta acentos (ç, ã, é) e emojis.</div></div>
              <div class="sl-flow-step"><div class="n">02 · CABEÇALHO</div><div class="h">Payload validado</div>
                <div class="p">Antes dos dados vêm 14 bytes: identificador <b>STGL</b>, versão, indicadores, comprimento e CRC32.</div></div>
              <div class="sl-flow-step"><div class="n">03 · BYTES → BITS</div><div class="h">Sequência binária</div>
                <div class="p">Cada byte dá 8 bits. Um píxel tem 3 canais (R, G, B), logo guarda 3 bits.</div></div>
              <div class="sl-flow-step"><div class="n">04 · LSB</div><div class="h">Bit menos significativo</div>
                <div class="p">Cada bit substitui o último bit de um canal de cor: o valor muda no máximo ±1 em 255.</div></div>
            </div>
            """
        )
        st.code(
            "novo_valor = (valor_original & 0b11111110) | bit_da_mensagem   # escrever\n"
            "bit_da_mensagem = valor & 1                                    # ler",
            language="python",
        )

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(key="card_how_text"):
            st.markdown("#### Do texto aos bits")
            word = st.text_input("Experimente um texto curto", value="Olá", max_chars=12, key="demo_word") or ""
            rows = []
            for ch in word:
                encoded = ch.encode("utf-8")
                rows.append(
                    f"<tr><td class='mono'>{escape(ch)}</td>"
                    f"<td class='mono'>{' '.join(f'{b:02X}' for b in encoded)}</td>"
                    f"<td class='mono'>{' '.join(f'{b:08b}' for b in encoded)}</td></tr>"
                )
            total_bits = len(word.encode("utf-8")) * 8
            st.html(
                "<table class='sl-table'><tr><th>Carácter</th><th>Bytes (hex)</th><th>Bits</th></tr>"
                + "".join(rows)
                + "</table>"
            )
            st.caption(
                f"{total_bits} bits de dados → {-(-total_bits // 3)} píxeis "
                f"(mais {HEADER_SIZE * 8} bits / {-(-HEADER_SIZE * 8 // 3)} píxeis de cabeçalho). "
                "Repare que “á” ocupa 2 bytes em UTF-8."
            )

    with right:
        with st.container(key="card_how_pixel"):
            st.markdown("#### Alterar o LSB de um píxel")
            colour = st.color_picker("Cor original do píxel", value="#3A7BD5", key="demo_colour")
            rgb = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
            cols = st.columns(3)
            bits = [
                cols[i].segmented_control(
                    f"Bit para {name}", options=[0, 1], default=(rgb[i] & 1) ^ 1,
                    required=True, key=f"demo_bit_{name}",
                )
                for i, name in enumerate("RGB")
            ]
            new = tuple((v & 0xFE) | (b if b is not None else 0) for v, b in zip(rgb, bits))
            rows = "".join(
                f"<tr><td><b>{name}</b></td><td class='mono'>{o}</td><td>{_bits_html(o)}</td>"
                f"<td>{_bits_html(n, o != n)}</td><td class='mono'>{n}</td>"
                f"<td class='mono'>{n - o:+d}</td></tr>"
                for name, o, n in zip("RGB", rgb, new)
            )
            st.html(
                "<table class='sl-table'><tr><th>Canal</th><th>Valor</th><th>Original</th>"
                "<th>Com mensagem</th><th>Novo</th><th>Δ</th></tr>" + rows + "</table>"
                f"""<div class="sl-swatches">
                  <div><span class="sl-swatch" style="background:rgb{rgb}"></span><div class="lbl">Original</div></div>
 <div><span class="sl-swatch" style="background:rgb{new}"></span><div class="lbl">Com 3 bits escondidos</div></div>
                </div>"""
            )
            st.caption("O olho humano não distingue as duas cores: é por isso que a técnica LSB passa despercebida.")

    with st.container(key="card_how_format"):
        st.markdown("#### Formato do payload StegoLab")
        st.html(
            """
            <table class="sl-table">
              <tr><th>Campo</th><th>Tamanho</th><th>Função</th></tr>
              <tr><td class="mono">MAGIC = "STGL"</td><td>4 bytes</td><td>Identifica uma imagem do StegoLab; sem ele, a extracção é recusada.</td></tr>
              <tr><td class="mono">VERSÃO</td><td>1 byte</td><td>Permite evoluir o formato no futuro.</td></tr>
              <tr><td class="mono">FLAGS</td><td>1 byte</td><td>Bit 0 = mensagem encriptada (pede palavra-passe).</td></tr>
              <tr><td class="mono">COMPRIMENTO</td><td>4 bytes</td><td>Quantos bytes ler — validado contra a capacidade da imagem.</td></tr>
              <tr><td class="mono">CRC32</td><td>4 bytes</td><td>Detecta dados truncados ou corrompidos.</td></tr>
              <tr><td class="mono">DADOS</td><td>N bytes</td><td>Mensagem em UTF-8 (ou sal + token Fernet, se encriptada).</td></tr>
            </table>
            """
        )
        st.caption("Capacidade = largura × altura × 3 bits ÷ 8 − 14 bytes de cabeçalho.")

    with st.container(key="card_how_compare"):
        st.markdown("#### Esteganografia ≠ Encriptação")
        st.html(
            """
            <div class="sl-compare">
              <div><h4>Esteganografia</h4>
                <p>Esconde a <b>existência</b> da mensagem. Quem vê a imagem não suspeita que há dados escondidos,
                mas quem souber onde procurar consegue lê-los.</p></div>
              <div><h4>Encriptação</h4>
                <p>Protege o <b>conteúdo</b>. Toda a gente vê que existe uma mensagem, mas sem a chave ela é ilegível.
                O StegoLab usa Fernet (AES + HMAC) com chave derivada por PBKDF2.</p></div>
            </div>
            """
        )
        st.html(
            """<div class="sl-prose"><p><b>Limitações importantes:</b></p><ul>
            <li>Não é indetectável: a análise estatística (esteganálise) pode revelar a alteração dos LSB.</li>
            <li>Redimensionar, recortar, editar ou comprimir com perdas (JPEG, redes sociais) destrói o payload.</li>
            <li>Sem encriptação, quem conhecer o formato consegue ler a mensagem.</li>
            <li>A combinação das duas técnicas aumenta a protecção, mas não oferece segurança absoluta.</li></ul></div>"""
        )


# --------------------------------------------------------------------------
# Separador 4 — Sobre o projecto
# --------------------------------------------------------------------------

def render_about_tab() -> None:
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        with st.container(key="card_about"):
            st.markdown("#### StegoLab — Protótipo de Esteganografia em Python")
            st.html(
                f"""<div class="sl-prose">
                <p>Trabalho prático da disciplina de <b>{ui.COURSE}</b> (Fundamentos de Segurança Informática),
                Licenciatura em Informática, {ui.INSTITUTION}.</p>
                <p>O objectivo é demonstrar, de forma visual e didáctica, como uma mensagem de texto pode ser
                escondida dentro de uma imagem e recuperada mais tarde, implementando o algoritmo LSB de raiz em Python.</p>
                <p>Este protótipo concentra-se na implementação em Python; não utiliza as ferramentas Steghide nem
                Stegosuite referidas noutra tarefa do enunciado.</p></div>"""
            )
            ui.chips(
                [
                    ("Docente", ui.TEACHER),
                    ("Ano", ui.YEAR),
                ]
            )
            ui.chips([("Integrante", m) for m in ui.MEMBERS])
    with right:
        with st.container(key="card_tech"):
            st.markdown("#### Tecnologias")
            st.html(
                """<table class="sl-table">
                <tr><td><b>Python 3.11+</b></td><td>Linguagem e algoritmo LSB explícito</td></tr>
                <tr><td><b>Pillow</b></td><td>Leitura, validação e gravação de imagens</td></tr>
                <tr><td><b>Streamlit</b></td><td>Interface web local</td></tr>
                <tr><td><b>cryptography</b></td><td>Encriptação opcional (Fernet + PBKDF2)</td></tr>
                <tr><td><b>FFmpeg</b></td><td>Opcional: leitura e escrita de vídeo</td></tr>
                <tr><td><b>pytest</b></td><td>Testes automatizados</td></tr></table>"""
            )
            st.caption("Nenhuma imagem ou mensagem é enviada para a Internet nem guardada em disco pela aplicação.")


# --------------------------------------------------------------------------

def render_headerbar(in_result: bool) -> None:
    """Cabeçalho fixo no topo, com o botão de navegação sempre visível."""
    with st.container(key="headerbar"):
        left, right = st.columns([3, 1.3], vertical_alignment="center")
        with left:
            ui.brand()
        with right:
            if in_result:
                st.button(
                    "Voltar ao laboratório",
                    icon=":material/arrow_back:",
                    width="stretch",
                    on_click=_go_lab,
                    key="nav_back",
                )
            elif "hide_result" in st.session_state:
                st.button(
                    "Ver resultado",
                    type="primary",
                    icon=":material/task_alt:",
                    width="stretch",
                    on_click=_go_result,
                    key="nav_result",
                )
            ui.header_tag()


def main() -> None:
    _state_defaults()
    ui.inject_css()

    in_result = st.session_state.view == "result" and "hide_result" in st.session_state
    if not in_result:
        st.session_state.view = "lab"
    render_headerbar(in_result)

    if in_result:
        render_result_page()
        # O laboratório continua a ser desenhado (escondido) para que a imagem
        # carregada e a mensagem não se percam ao voltar.
        st.html("<style>.st-key-lab_view { display: none; }</style>")

    with st.container(key="lab_view"):
        tabs = st.tabs(
            [
                ":material/lock: Esconder mensagem",
                ":material/lock_open: Extrair mensagem",
            ]
        )
        with tabs[0]:
            render_hide_tab()
        with tabs[1]:
            render_extract_tab()
    ui.footer()

    if st.session_state.scroll_nonce:
        ui.scroll_to_top(st.session_state.scroll_nonce)


main()
