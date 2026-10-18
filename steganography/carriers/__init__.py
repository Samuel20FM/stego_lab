"""Detecção do tipo de ficheiro (pelo conteúdo) e operações genéricas.

    carrier = open_carrier(dados, "foto.png")
    saida = hide(carrier, Secret.text("olá"), password="...")
    resultado = reveal(open_carrier(saida.data), password="...")
"""

from __future__ import annotations

from ..errors import CapacityError, InvalidFileError
from ..image_utils import MAX_FILE_BYTES
from ..payload import HEADER_SIZE
from ..secret import RevealResult, Secret, make_payload, open_payload
from .archive import ZipCarrier, sniff_zip
from .audio import WavCarrier
from .base import Carrier, LsbCarrier, Output
from .image import ImageCarrier
from .pdf import PdfCarrier, sniff_pdf
from .text import TextCarrier, looks_like_text
from .video import VIDEO_MAX_BYTES, VideoCarrier, ffmpeg_available, sniff_video

__all__ = [
    "COVER_TYPES",
    "Carrier",
    "ImageCarrier",
    "LsbCarrier",
    "Output",
    "PdfCarrier",
    "TextCarrier",
    "VIDEO_MAX_BYTES",
    "VideoCarrier",
    "WavCarrier",
    "ZipCarrier",
    "ffmpeg_available",
    "hide",
    "open_carrier",
    "reveal",
]

# Extensões sugeridas no selector de ficheiros (a validação real é pelo conteúdo).
COVER_TYPES = [
    "png", "bmp", "tif", "tiff", "webp", "jpg", "jpeg",
    "wav",
    "mp4", "mov", "m4v", "mkv", "webm",
    "txt", "md", "csv",
    "pdf",
    "docx", "xlsx", "pptx", "odt", "ods", "odp", "epub", "zip",
]

_IMAGE_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*", b"GIF8")


def _is_image(head: bytes) -> bool:
    if head.startswith(_IMAGE_MAGIC):
        return True
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return head[:2] == b"BM" and head[6:10] == b"\x00\x00\x00\x00"  # campos reservados do BMP


def _lossy_audio(head: bytes) -> str | None:
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "MP3"
    if head[:4] == b"OggS":
        return "OGG"
    if head[:4] == b"fLaC":
        return "FLAC"
    return None


def open_carrier(data: bytes, filename: str = "") -> Carrier:
    """Identifica o tipo de ficheiro pelos primeiros bytes (nunca pela extensão)."""
    if not data:
        raise InvalidFileError("O ficheiro está vazio.")
    head = data[:16]
    video = sniff_video(head)
    limit = VIDEO_MAX_BYTES if video else MAX_FILE_BYTES
    if len(data) > limit:
        raise InvalidFileError(f"O ficheiro excede o limite de {limit // (1024 * 1024)} MB.")

    if _is_image(head):
        return ImageCarrier(data, filename)
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return WavCarrier(data, filename)
    if video:
        return VideoCarrier(data, filename)
    if sniff_pdf(data):
        return PdfCarrier(data, filename)
    if sniff_zip(head):
        return ZipCarrier(data, filename)
    lossy = _lossy_audio(head)
    if lossy:
        raise InvalidFileError(
            f"Áudio {lossy} não é suportado: converta-o para WAV (PCM) antes de esconder."
        )
    if looks_like_text(data):
        return TextCarrier(data, filename)
    raise InvalidFileError(
        "Formato não reconhecido. Use uma imagem, um WAV, um vídeo, um texto, um PDF ou um documento Office."
    )


def hide(carrier: Carrier, secret: Secret, password: str | None = None, fmt: str | None = None) -> Output:
    payload = make_payload(secret, password)
    needed, available = len(payload) - HEADER_SIZE, carrier.capacity()
    if needed > available:
        raise CapacityError(
            f"O segredo precisa de {needed:,} bytes, mas este ficheiro só suporta "
            f"{available:,} bytes. Use um ficheiro maior ou um segredo mais pequeno."
        )
    return carrier.embed(payload, fmt)


def reveal(carrier: Carrier, password: str | None = None, now: float | None = None) -> RevealResult:
    header, data = carrier.extract()
    return open_payload(header, data, password, now)
