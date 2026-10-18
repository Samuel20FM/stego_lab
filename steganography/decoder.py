"""Extracção LSB: recuperar a mensagem a partir dos bits menos significativos.

1. Lê os primeiros 112 LSB (14 bytes) e valida o cabeçalho.
2. Usa o comprimento do cabeçalho para ler *apenas* os bits necessários.
3. Verifica o CRC32, desencripta (se necessário) e descodifica em UTF-8.
"""

from __future__ import annotations

from PIL import Image

from .errors import CorruptPayloadError
from .image_utils import split_channels
from .payload import HEADER_BITS, HEADER_SIZE, Header, bits_to_bytes, parse_header
from .secret import RevealResult, open_payload

__all__ = [
    "RevealResult",
    "extract_bits",
    "read_header",
    "read_lsb_header",
    "read_lsb_payload",
    "reveal_message",
]


def extract_bits(carrier: bytes, start: int, count: int) -> list[int]:
    """Lê ``count`` LSB a partir da posição ``start``, sem ultrapassar os dados."""
    if start < 0 or count < 0 or start + count > len(carrier):
        raise CorruptPayloadError("Tentativa de leitura fora dos limites do ficheiro.")
    return [carrier[i] & 1 for i in range(start, start + count)]


def read_lsb_header(carrier: bytes) -> Header:
    """Valida o cabeçalho escrito nos LSB de ``carrier`` (bytes portadores)."""
    if len(carrier) < HEADER_BITS:
        return parse_header(b"", 0)  # lança NoPayloadError
    raw = bits_to_bytes(extract_bits(carrier, 0, HEADER_BITS))
    return parse_header(raw, len(carrier) // 8 - HEADER_SIZE)


def read_lsb_payload(carrier: bytes) -> tuple[Header, bytes]:
    header = read_lsb_header(carrier)
    data = bits_to_bytes(extract_bits(carrier, HEADER_BITS, header.length * 8))
    return header, data


def _carrier(image: Image.Image) -> bytes:
    rgb, _ = split_channels(image)
    return rgb.tobytes()


def read_header(image: Image.Image) -> Header:
    """Lê e valida apenas o cabeçalho (útil para saber se está encriptado).

    Lança ``NoPayloadError`` se a imagem não tiver uma mensagem StegoLab.
    """
    return read_lsb_header(_carrier(image))


def reveal_message(
    image: Image.Image, password: str | None = None, now: float | None = None
) -> RevealResult:
    header, data = read_lsb_payload(_carrier(image))
    return open_payload(header, data, password, now)
