"""Texto: caracteres Unicode de largura zero (invisíveis).

Cada carácter invisível representa 2 bits, por isso cada byte do payload passa
a ser uma sequência de 4 caracteres que não ocupam espaço no ecrã:

    U+200B (00)   U+200C (01)   U+200D (10)   U+2060 (11)

A sequência é inserida a seguir ao primeiro espaço do texto. O texto visível
fica exactamente igual, mas o ficheiro cresce 12 bytes por cada byte escondido
(cada carácter invisível ocupa 3 bytes em UTF-8).
"""

from __future__ import annotations

import codecs
import unicodedata
from pathlib import PurePath

from ..errors import InvalidFileError, NoPayloadError
from ..payload import HEADER_SIZE, MAGIC, Header, split_payload
from .base import Carrier, Output

ZW_CHARS = ("​", "‌", "‍", "⁠")
_ZW_VALUE = {c: i for i, c in enumerate(ZW_CHARS)}
TEXT_MAX_DATA = 64 * 1024
TEXT_EXTS = {"txt", "md", "csv", "log", "html", "htm", "json", "xml"}
_MIN_RUN = HEADER_SIZE * 4


def encode_zero_width(payload: bytes) -> str:
    return "".join(ZW_CHARS[(byte >> shift) & 0b11] for byte in payload for shift in (6, 4, 2, 0))


def decode_zero_width(chars: str) -> bytes:
    out = bytearray()
    for i in range(0, len(chars) - len(chars) % 4, 4):
        byte = 0
        for c in chars[i : i + 4]:
            byte = (byte << 2) | _ZW_VALUE[c]
        out.append(byte)
    return bytes(out)


def looks_like_text(data: bytes) -> bool:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    if "\x00" in text:
        return False
    controls = sum(1 for c in text if unicodedata.category(c) == "Cc" and c not in "\t\n\r\f")
    return controls <= max(2, len(text) // 100)


class TextCarrier(Carrier):
    kind = "text"
    label = "Texto"
    technique = "Caracteres Unicode invisíveis (largura zero)"

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        if not looks_like_text(data):
            raise InvalidFileError("O ficheiro não é texto UTF-8 válido.")
        self.bom = data.startswith(codecs.BOM_UTF8)
        self.text = data.decode("utf-8-sig")
        if not self.text.strip():
            raise InvalidFileError("O texto de cobertura está vazio.")

    def payload_run(self) -> tuple[int, int] | None:
        """Posição da sequência invisível do StegoLab (início, fim), se existir."""
        text, i = self.text, 0
        while i < len(text):
            if text[i] in _ZW_VALUE:
                j = i
                while j < len(text) and text[j] in _ZW_VALUE:
                    j += 1
                if j - i >= _MIN_RUN and decode_zero_width(text[i : i + 16]) == MAGIC:
                    return i, j
                i = j
            else:
                i += 1
        return None

    def capacity(self) -> int:
        return TEXT_MAX_DATA

    @property
    def ext(self) -> str:
        suffix = PurePath(self.filename).suffix.lower().lstrip(".")
        return suffix if suffix in TEXT_EXTS else "txt"

    def embed(self, payload: bytes, fmt: str | None = None) -> Output:
        base = self.text
        run = self.payload_run()
        if run:  # substitui um segredo anterior em vez de acumular
            base = base[: run[0]] + base[run[1] :]
        pos = base.find(" ") + 1 or len(base)
        stego = base[:pos] + encode_zero_width(payload) + base[pos:]
        data = (codecs.BOM_UTF8 if self.bom else b"") + stego.encode("utf-8")
        return Output(data, self.ext, "text/plain")

    def extract(self) -> tuple[Header, bytes]:
        run = self.payload_run()
        if run is None:
            raise NoPayloadError("Não foi encontrada nenhuma mensagem StegoLab neste texto.")
        start, end = run
        return split_payload(decode_zero_width(self.text[start:end]))

    def details(self) -> list[tuple[str, str]]:
        visible = "".join(c for c in self.text if c not in _ZW_VALUE)
        return [
            ("Linhas", f"{visible.count(chr(10)) + 1:,}".replace(",", " ")),
            ("Palavras", f"{len(visible.split()):,}".replace(",", " ")),
            ("Caracteres", f"{len(visible):,}".replace(",", " ")),
        ]
