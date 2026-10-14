"""StegoLab — Laboratório de Esteganografia (interface Streamlit).

Executar:  streamlit run app.py

A lógica de esteganografia vive no pacote ``steganography`` e não depende do
Streamlit; este ficheiro apenas trata da interface.
"""

from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image, ImageChops

from steganography import (
    MAX_MESSAGE_BYTES,
    OUTPUT_FORMATS,
    CorruptPayloadError,
    NoPayloadError,
    StegoError,
    WrongPasswordError,
    capacity_bytes,
    hide_message,
    image_to_bytes,
    load_image,
    read_header,
    required_bytes,
    reveal_message,
)
from steganography.payload import HEADER_SIZE
from ui import components as ui

st.set_page_config(
    page_title="StegoLab — Laboratório de Esteganografia",
    page_icon=str(ui.FAVICON),
    layout="wide",
    initial_sidebar_state="collapsed",
)

UPLOAD_TYPES = ["png", "bmp", "tif", "tiff", "webp", "jpg", "jpeg"]
FORMAT_LABELS = {
    "PNG": "PNG (recomendado)",
    "BMP": "BMP",
    "TIFF": "TIFF",
    "WEBP": "WebP sem perdas",
}


# --------------------------------------------------------------------------
# Utilitários de estado e de imagem
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


@st.cache_data(show_spinner=False, max_entries=6)
def _load(data: bytes):
    """Valida o ficheiro carregado (pelo conteúdo, não pela extensão)."""
    return load_image(data)


def _digest(*parts: bytes | str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part if isinstance(part, bytes) else part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _image_chips(info) -> None:
    ui.chips(
        [
            ("Dimensões", f"{info.width}×{info.height}"),
            ("Formato", info.format),
            ("Modo", info.mode),
            ("Tamanho", ui.fmt_bytes(info.file_size or 0)),
        ]
    )


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
# Separador 1 — Esconder mensagem
# --------------------------------------------------------------------------

def render_hide_tab() -> None:
    nonce = st.session_state.hide_nonce
    left, right = st.columns([1, 1.15], gap="large")

    img = info = None
    data = b""
    with left:
        with st.container(key="card_hide_image"):
            ui.step(1, "Imagem de cobertura", "PNG · BMP · TIFF · WebP · JPEG")
            upload = st.file_uploader(
                "Carregar imagem",
                type=UPLOAD_TYPES,
                key=f"hide_upload_{nonce}",
                help="A imagem é validada pelo conteúdo. O resultado é sempre gravado num formato sem perdas.",
                label_visibility="collapsed",
            )
            if upload is None:
                ui.empty_preview("Carregue uma imagem para ver a pré-visualização e a capacidade.")
            else:
                data = upload.getvalue()
                try:
                    img, info = _load(data)
                except Exception as exc:
                    _show_error(exc)
                    img = None
                if img is not None:
                    st.image(img, width="stretch", caption=upload.name)
                    _image_chips(info)
                    cap = capacity_bytes(img)
                    ui.chips(
                        [
                            ("Capacidade", ui.fmt_bytes(cap), "ok"),
                            ("≈ caracteres simples", ui.fmt_int(min(cap, MAX_MESSAGE_BYTES))),
                            ("Bits disponíveis", ui.fmt_int(img.width * img.height * 3)),
                        ]
                    )
                    if info.lossy:
                        ui.notice(
                            "info",
                            "Imagem JPEG aceite como ponto de partida",
                            "O resultado será gravado num formato sem perdas (PNG por omissão). "
                            "Nunca volte a converter a imagem final para JPEG.",
                        )

    with right:
        with st.container(key="card_hide_message"):
            ui.step(2, "Mensagem secreta")
            message = st.text_area(
                "Mensagem secreta",
                key=f"hide_message_{nonce}",
                height=170,
                placeholder="Escreva aqui a mensagem a esconder… (acentos e emojis são suportados)",
                label_visibility="collapsed",
                help="Ctrl+Enter actualiza o contador e a capacidade.",
            ) or ""
            nbytes = len(message.encode("utf-8"))
            ui.counter(len(message), nbytes)

            encrypt = st.toggle(
                "Proteger o conteúdo com palavra-passe (encriptação Fernet)",
                key=f"hide_encrypt_{nonce}",
                help="Opcional. A mensagem é encriptada antes de ser escondida nos píxeis.",
            )
            password = confirm = ""
            if encrypt:
                c1, c2 = st.columns(2)
                password = c1.text_input("Palavra-passe", type="password", key=f"hide_pw_{nonce}")
                confirm = c2.text_input("Confirmar palavra-passe", type="password", key=f"hide_pw2_{nonce}")

            fmt = st.segmented_control(
                "Formato do ficheiro de saída",
                options=list(OUTPUT_FORMATS),
                format_func=FORMAT_LABELS.get,
                default="PNG",
                required=True,
                key=f"hide_fmt_{nonce}",
                help="Apenas formatos sem perdas. JPEG não é oferecido: a compressão destrói os bits escondidos.",
            ) or "PNG"

            # ---- Capacidade e validação antes de permitir a codificação ----
            problems: list[str] = []
            if img is not None:
                total = capacity_bytes(img) + HEADER_SIZE
                used = required_bytes(message, encrypt) if message else HEADER_SIZE
                ui.capacity_meter(used, total, encrypted=encrypt)
                if used > total:
                    problems.append(
                        f"A mensagem ultrapassa a capacidade da imagem em {ui.fmt_bytes(used - total)}. "
                        "Use uma imagem maior ou encurte a mensagem."
                    )
            if nbytes > MAX_MESSAGE_BYTES:
                problems.append(f"O limite da aplicação é {ui.fmt_int(MAX_MESSAGE_BYTES)} bytes por mensagem.")
            if encrypt and password and confirm and password != confirm:
                problems.append("As palavras-passe não coincidem.")
            if encrypt and password and len(password) < 4:
                problems.append("Use uma palavra-passe com pelo menos 4 caracteres.")
            for p in problems:
                ui.notice("warning", "Atenção", p)

            # O botão fica activo assim que existe imagem: o Streamlit só confirma
            # o texto ao sair do campo, por isso a validação final é feita no clique.
            b1, b2 = st.columns([2, 1])
            go = b1.button(
                "Esconder mensagem",
                type="primary",
                icon=":material/visibility_off:",
                width="stretch",
                disabled=img is None,
                key=f"hide_go_{nonce}",
            )
            b2.button(
                "Limpar",
                icon=":material/restart_alt:",
                width="stretch",
                on_click=_reset_hide,
                key=f"hide_clear_{nonce}",
            )
            if img is None:
                st.caption("Carregue uma imagem para começar.")

            error = None
            if go:
                if not message.strip():
                    error = "Escreva uma mensagem antes de a esconder."
                elif problems:
                    error = problems[0]
                elif encrypt and not password:
                    error = "Introduza uma palavra-passe ou desactive a encriptação."
                elif encrypt and password != confirm:
                    error = "Confirme a palavra-passe: os dois campos têm de ser iguais."
                if error:
                    ui.notice("error", "Não é possível esconder a mensagem", error)

    signature = _digest(data, message, fmt, "enc" if encrypt else "plain")

    if go and img is not None and error is None:
        try:
            with st.spinner("A esconder a mensagem nos bits menos significativos…"):
                pw = password if encrypt else None
                stego = hide_message(img, message, password=pw)
                out = image_to_bytes(stego, fmt)
                # Autoverificação: reabre o ficheiro gerado e extrai a mensagem.
                check_img, _ = load_image(out)
                verified = reveal_message(check_img, password=pw).message == message
                diff_img, changed_px, changed_ch = _diff_map(img, stego)
            total = capacity_bytes(img) + HEADER_SIZE
            used = required_bytes(message, encrypt)
            stem = Path(upload.name).stem or "imagem"
            st.session_state.hide_result = {
                "signature": signature,
                "bytes": out,
                "format": fmt,
                "filename": f"{stem}_stego.{OUTPUT_FORMATS[fmt]['ext']}",
                "mime": OUTPUT_FORMATS[fmt]["mime"],
                "original": img.convert("RGBA" if "A" in img.mode else "RGB"),
                "stego": stego,
                "diff": diff_img,
                "changed_px": changed_px,
                "changed_ch": changed_ch,
                "bits": used * 8,
                "pct": used / total * 100,
                "encrypted": encrypt,
                "verified": verified,
                "src_name": upload.name,
                "src_format": info.format,
                "src_size": info.file_size or 0,
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
            "Use o botão “Ver resultado” no topo da página para ver as imagens e descarregar o ficheiro.",
        )


def render_result_page() -> None:
    """Página dedicada ao resultado da operação "Esconder mensagem"."""
    r = st.session_state.hide_result
    with st.container(key="cardresult_hide"):
        ui.step("✓", "Resultado", f"Imagem de partida: {r['src_name']} · a original não foi alterada")
        if r["verified"]:
            ui.notice(
                "success",
                "Mensagem escondida com sucesso",
                "O ficheiro gerado foi reaberto e a mensagem foi extraída de novo para confirmar a integridade."
                + (" O conteúdo está encriptado." if r["encrypted"] else ""),
            )
        else:
            ui.notice("warning", "A verificação automática falhou", "Tente novamente ou escolha o formato PNG.")

        ui.stats(
            [
                ("Bits escritos", ui.fmt_int(r["bits"])),
                ("Canais alterados", ui.fmt_int(r["changed_ch"])),
                ("Píxeis alterados", ui.fmt_int(r["changed_px"])),
                ("Capacidade usada", ui.fmt_pct(r["pct"])),
            ]
        )

        c1, c2, c3 = st.columns(3, gap="medium")
        c1.image(r["original"], width="stretch", caption=f"Original · {r['src_format']} · {ui.fmt_bytes(r['src_size'])}")
        c2.image(r["stego"], width="stretch", caption=f"Com mensagem · {r['format']} · {ui.fmt_bytes(len(r['bytes']))}")
        c3.image(r["diff"], width="stretch", caption=f"Zoom ×{ZOOM_SCALE} no canto superior esquerdo ({ZOOM_W}×{ZOOM_H} píxeis): a verde, os píxeis alterados")
        st.caption(
            "As duas imagens são visualmente idênticas: cada canal muda no máximo 1 unidade em 255. "
            "Os bits são escritos linha a linha a partir do canto superior esquerdo; cerca de metade "
            "já tinha o valor certo, por isso há menos canais alterados do que bits escritos."
        )

        d1, d2 = st.columns([2, 3])
        d1.download_button(
            f"Descarregar imagem {r['format']}",
            data=r["bytes"],
            file_name=r["filename"],
            mime=r["mime"],
            type="primary",
            icon=":material/download:",
            width="stretch",
            on_click="ignore",
        )
        with d2:
            ui.notice(
                "info",
                "Partilhe o ficheiro sem o editar",
                "Redimensionar, recortar, editar ou comprimir (JPEG, WhatsApp, redes sociais) destrói a mensagem.",
            )

    n1, n2, _ = st.columns([1, 1, 1.4])
    n1.button("Voltar e editar", icon=":material/edit:", width="stretch", on_click=_go_lab, key="result_back")
    n2.button("Esconder outra mensagem", icon=":material/add:", width="stretch", on_click=_new_hide, key="result_new")


# --------------------------------------------------------------------------
# Separador 2 — Extrair mensagem
# --------------------------------------------------------------------------

def render_extract_tab() -> None:
    nonce = st.session_state.extract_nonce
    left, right = st.columns([1, 1.15], gap="large")

    img = info = header = None
    data = b""
    with left:
        with st.container(key="card_extract_image"):
            ui.step(1, "Imagem com mensagem", "Ficheiro gerado pelo StegoLab")
            upload = st.file_uploader(
                "Carregar imagem com mensagem",
                type=UPLOAD_TYPES,
                key=f"extract_upload_{nonce}",
                label_visibility="collapsed",
            )
            if upload is None:
                ui.empty_preview("Carregue a imagem que contém a mensagem escondida.")
            else:
                data = upload.getvalue()
                try:
                    img, info = _load(data)
                except Exception as exc:
                    _show_error(exc)
                if img is not None:
                    st.image(img, width="stretch", caption=upload.name)
                    _image_chips(info)

    with right:
        with st.container(key="card_extract_result"):
            ui.step(2, "Recuperar a mensagem")
            password = ""
            if img is None:
                ui.empty_preview("A análise do cabeçalho aparece aqui.")
            else:
                try:
                    header = read_header(img)
                except NoPayloadError:
                    ui.notice(
                        "error",
                        "Nenhuma mensagem StegoLab encontrada",
                        "O identificador “STGL” não está presente nos bits menos significativos. "
                        "A imagem pode não ter mensagem, ou ter sido convertida, redimensionada ou comprimida.",
                    )
                except CorruptPayloadError as exc:
                    ui.notice("error", "Cabeçalho encontrado, mas inválido", str(exc))
                except Exception as exc:
                    _show_error(exc)

                if info and info.lossy and header is None:
                    ui.notice(
                        "warning",
                        "Ficheiro JPEG",
                        "A compressão JPEG altera os bits menos significativos; mensagens escondidas não sobrevivem.",
                    )

                if header is not None:
                    ui.chips(
                        [
                            ("Identificador", "STGL ✓", "ok"),
                            ("Versão", str(header.version)),
                            ("Dados", ui.fmt_bytes(header.length)),
                            ("Encriptada", "sim" if header.encrypted else "não", "lock" if header.encrypted else ""),
                        ]
                    )
                    if header.encrypted:
                        password = st.text_input(
                            "Palavra-passe",
                            type="password",
                            key=f"extract_pw_{nonce}",
                            help="Esta mensagem foi protegida com encriptação Fernet.",
                        )

            b1, b2 = st.columns([2, 1])
            go = b1.button(
                "Extrair mensagem",
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
                    with st.spinner("A ler os bits menos significativos…"):
                        res = reveal_message(img, password=password or None)
                    st.session_state.extract_result = {
                        "signature": signature,
                        "message": res.message,
                        "encrypted": res.encrypted,
                        "bytes": res.data_bytes,
                    }
                except WrongPasswordError as exc:
                    st.session_state.pop("extract_result", None)
                    ui.notice("error", "Palavra-passe incorrecta", str(exc))
                except Exception as exc:
                    st.session_state.pop("extract_result", None)
                    _show_error(exc)

            result = st.session_state.get("extract_result")
            if result and result["signature"] == signature:
                ui.notice(
                    "success",
                    "Mensagem recuperada",
                    f"{ui.fmt_int(len(result['message']))} caracteres · {ui.fmt_bytes(result['bytes'])} lidos"
                    + (" · desencriptada com sucesso" if result["encrypted"] else ""),
                )
                ui.secret_box(result["message"])
                c1, c2 = st.columns(2)
                with c1:
                    ui.copy_button(result["message"], key=f"copy{nonce}")
                c2.download_button(
                    "Guardar como .txt",
                    data=result["message"].encode("utf-8"),
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
                ":material/school: Como funciona?",
                ":material/info: Sobre o projecto",
            ]
        )
        with tabs[0]:
            render_hide_tab()
        with tabs[1]:
            render_extract_tab()
        with tabs[2]:
            render_how_tab()
        with tabs[3]:
            render_about_tab()
    ui.footer()

    if st.session_state.scroll_nonce:
        ui.scroll_to_top(st.session_state.scroll_nonce)


main()
