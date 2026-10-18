"""PDF: comentários inseridos antes da palavra-chave ``startxref``.

Em PDF, tudo o que começa por ``%`` até ao fim da linha é um comentário e é
ignorado pelos leitores. O payload é codificado em base64 e escrito em linhas
``%STGL:...`` logo antes de ``startxref``. Como fica *depois* da tabela de
referências, nenhum deslocamento (offset) do ficheiro muda e o PDF continua
válido. Não é LSB: é ocultação na estrutura do ficheiro, visível para quem o
abrir num editor de texto.
"""

from __future__ import annotations

import base64
import binascii
import re

from ..errors import CorruptPayloadError, InvalidFileError, NoPayloadError
from ..payload import MAX_DATA_BYTES, Header, split_payload
from .base import Carrier, Output

_BLOCK = re.compile(rb"%STGL-BEGIN\r?\n((?:%STGL:[A-Za-z0-9+/=]*\r?\n)*)%STGL-END\r?\n")
_LINE = re.compile(rb"%STGL:([A-Za-z0-9+/=]*)")
_LINE_WIDTH = 76


def sniff_pdf(data: bytes) -> bool:
    return b"%PDF-" in data[:1024]


class PdfCarrier(Carrier):
    kind = "pdf"
    label = "Documento PDF"
    technique = "Comentários na estrutura do PDF"

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        if not sniff_pdf(data):
            raise InvalidFileError("O ficheiro não é um PDF válido.")
        self.xref_pos = data.rfind(b"startxref")
        if self.xref_pos < 0 or b"%%EOF" not in data[self.xref_pos :]:
            raise InvalidFileError("O PDF está incompleto (falta startxref ou %%EOF).")
        m = re.search(rb"%PDF-(\d\.\d)", data[:1024])
        self.version = m.group(1).decode() if m else "?"
        self.pages = len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", data))

    def capacity(self) -> int:
        return MAX_DATA_BYTES

    def embed(self, payload: bytes, fmt: str | None = None) -> Output:
        base = self.data
        old = _BLOCK.search(base)
        if old:
            # Só é seguro remover o bloco se for o nosso, mesmo antes do último startxref.
            if old.end() != self.xref_pos:
                raise InvalidFileError(
                    "Este PDF já contém um segredo StegoLab e foi alterado depois. "
                    "Use o PDF original."
                )
            base = base[: old.start()] + base[old.end() :]
        pos = base.rfind(b"startxref")
        b64 = base64.b64encode(payload)
        lines = b"".join(
            b"%STGL:" + b64[i : i + _LINE_WIDTH] + b"\n" for i in range(0, len(b64), _LINE_WIDTH)
        )
        sep = b"" if base[:pos].endswith((b"\n", b"\r")) else b"\n"
        block = sep + b"%STGL-BEGIN\n" + lines + b"%STGL-END\n"
        return Output(base[:pos] + block + base[pos:], "pdf", "application/pdf")

    def extract(self) -> tuple[Header, bytes]:
        m = _BLOCK.search(self.data)
        if m is None:
            raise NoPayloadError("Não foi encontrada nenhuma mensagem StegoLab neste PDF.")
        try:
            raw = base64.b64decode(b"".join(_LINE.findall(m.group(1))), validate=True)
        except (binascii.Error, ValueError):
            raise CorruptPayloadError("O bloco escondido no PDF está corrompido.") from None
        return split_payload(raw)

    def details(self) -> list[tuple[str, str]]:
        return [("Versão", f"PDF {self.version}"), ("Páginas", str(self.pages or "?"))]
