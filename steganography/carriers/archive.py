"""Documentos Office (DOCX, XLSX, PPTX, ODT, …) e outros ficheiros ZIP.

Estes documentos são arquivos ZIP. O formato ZIP permite um comentário de até
65 535 bytes no fim do ficheiro, que o Word, o Excel e o LibreOffice ignoram.
O StegoLab escreve aí o payload: os ficheiros internos não são tocados.
Voltar a gravar o documento no Word apaga o comentário (e a mensagem).
"""

from __future__ import annotations

import io
import zipfile

from ..errors import InvalidFileError, NoPayloadError
from ..payload import HEADER_SIZE, MAGIC, Header, split_payload
from .base import Carrier, Output

ZIP_COMMENT_MAX = 65_535
MAX_MEMBERS = 20_000

_OOXML = {
    "word/document.xml": ("docx", "Documento Word",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "xl/workbook.xml": ("xlsx", "Folha de cálculo Excel",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "ppt/presentation.xml": ("pptx", "Apresentação PowerPoint",
                             "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
}
_ODF = {
    "application/vnd.oasis.opendocument.text": ("odt", "Documento ODT"),
    "application/vnd.oasis.opendocument.spreadsheet": ("ods", "Folha de cálculo ODS"),
    "application/vnd.oasis.opendocument.presentation": ("odp", "Apresentação ODP"),
    "application/epub+zip": ("epub", "Livro EPUB"),
}


def sniff_zip(head: bytes) -> bool:
    return head[:4] in (b"PK\x03\x04", b"PK\x05\x06")


class ZipCarrier(Carrier):
    kind = "zip"
    technique = "Comentário do arquivo ZIP"

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                infos = zf.infolist()
                if len(infos) > MAX_MEMBERS:
                    raise InvalidFileError("O arquivo contém ficheiros internos a mais.")
                names = {i.filename for i in infos}
                self.comment = zf.comment
                mimetype = b""
                if "mimetype" in names and zf.getinfo("mimetype").file_size <= 200:
                    mimetype = zf.read("mimetype").strip()
        except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, EOFError):
            raise InvalidFileError("O arquivo ZIP/Office está danificado.") from None
        self.members = len(infos)

        self.ext, self.label, self.mime = "zip", "Arquivo ZIP", "application/zip"
        for marker, spec in _OOXML.items():
            if marker in names:
                self.ext, self.label, self.mime = spec
                break
        else:
            odf = _ODF.get(mimetype.decode("ascii", "ignore"))
            if odf:
                self.ext, self.label = odf
                self.mime = mimetype.decode("ascii")

    def capacity(self) -> int:
        return ZIP_COMMENT_MAX - HEADER_SIZE

    def embed(self, payload: bytes, fmt: str | None = None) -> Output:
        buf = io.BytesIO(self.data)
        with zipfile.ZipFile(buf, "a") as zf:
            zf.comment = payload  # só o registo final do ZIP é reescrito
        return Output(buf.getvalue(), self.ext, self.mime)

    def extract(self) -> tuple[Header, bytes]:
        if not self.comment.startswith(MAGIC):
            raise NoPayloadError("Não foi encontrada nenhuma mensagem StegoLab neste documento.")
        return split_payload(self.comment)

    def details(self) -> list[tuple[str, str]]:
        return [("Tipo", self.ext.upper()), ("Ficheiros internos", str(self.members))]
