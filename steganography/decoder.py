"""Extracção LSB: recuperar a mensagem a partir dos bits menos significativos.

1. Lê os primeiros 112 LSB (14 bytes) e valida o cabeçalho.
2. Usa o comprimento do cabeçalho para ler *apenas* os bits necessários.
3. Verifica o CRC32, desencripta (se necessário) e descodifica em UTF-8.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from . import crypto
from .errors import CorruptPayloadError, PasswordRequiredError
from .image_utils import capacity_bytes, split_channels
from .payload import HEADER_BITS, Header, bits_to_bytes, parse_header, verify_data


@dataclass(frozen=True)
class RevealResult:
    message: str
    encrypted: bool
    data_bytes: int  # bytes de dados lidos (sem cabeçalho)


def extract_bits(carrier: bytes, start: int, count: int) -> list[int]:
    """Lê ``count`` LSB a partir da posição ``start``, sem ultrapassar os dados."""
    if start < 0 or count < 0 or start + count > len(carrier):
        raise CorruptPayloadError("Tentativa de leitura fora dos limites da imagem.")
    return [carrier[i] & 1 for i in range(start, start + count)]


def _carrier(image: Image.Image) -> bytes:
    rgb, _ = split_channels(image)
    return rgb.tobytes()


def _parse_header(carrier: bytes, image: Image.Image) -> Header:
    if len(carrier) < HEADER_BITS:
        return parse_header(b"", 0)  # lança NoPayloadError
    raw = bits_to_bytes(extract_bits(carrier, 0, HEADER_BITS))
    return parse_header(raw, capacity_bytes(image))


def read_header(image: Image.Image) -> Header:
    """Lê e valida apenas o cabeçalho (útil para saber se está encriptado).

    Lança ``NoPayloadError`` se a imagem não tiver uma mensagem StegoLab.
    """
    return _parse_header(_carrier(image), image)


def reveal_message(image: Image.Image, password: str | None = None) -> RevealResult:
    carrier = _carrier(image)
    header = _parse_header(carrier, image)

    data = bits_to_bytes(extract_bits(carrier, HEADER_BITS, header.length * 8))
    verify_data(header, data)

    if header.encrypted:
        if not password:
            raise PasswordRequiredError(
                "Esta mensagem está encriptada. Introduza a palavra-passe."
            )
        data = crypto.decrypt(data, password)

    try:
        message = data.decode("utf-8")
    except UnicodeDecodeError:
        raise CorruptPayloadError(
            "Os dados extraídos não formam texto UTF-8 válido."
        ) from None
    return RevealResult(message=message, encrypted=header.encrypted, data_bytes=header.length)
