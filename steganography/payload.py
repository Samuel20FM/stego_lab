"""Formato do payload e conversão entre bytes e bits.

Estrutura do payload escondido na imagem (14 bytes de cabeçalho + dados):

    +--------+---------+-------+-------------+-----------+-------------+
    | MAGIC  | VERSÃO  | FLAGS | COMPRIMENTO | CRC32     | DADOS       |
    | 4 B    | 1 B     | 1 B   | 4 B (BE)    | 4 B (BE)  | N bytes     |
    | "STGL" | 0x01    | bit0= | N           | dos DADOS | mensagem    |
    |        |         | encr. |             |           | (ou cifra)  |
    +--------+---------+-------+-------------+-----------+-------------+

* MAGIC identifica imagens produzidas pelo StegoLab.
* COMPRIMENTO diz exactamente quantos bytes ler — nunca lemos "a imagem toda".
* CRC32 detecta dados truncados ou alterados (por ex., compressão JPEG).
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from .errors import CorruptPayloadError, NoPayloadError

MAGIC = b"STGL"
VERSION = 1
FLAG_ENCRYPTED = 0b0000_0001
KNOWN_FLAGS = FLAG_ENCRYPTED

# ">4sBBII": magic (4s), versão (B), flags (B), comprimento (I), crc32 (I)
_HEADER_STRUCT = struct.Struct(">4sBBII")
HEADER_SIZE = _HEADER_STRUCT.size  # 14 bytes
HEADER_BITS = HEADER_SIZE * 8  # 112 bits

# Limite de segurança para os dados (após encriptação, se existir).
MAX_DATA_BYTES = 256 * 1024


@dataclass(frozen=True)
class Header:
    version: int
    flags: int
    length: int
    crc32: int

    @property
    def encrypted(self) -> bool:
        return bool(self.flags & FLAG_ENCRYPTED)


def build_payload(data: bytes, encrypted: bool = False) -> bytes:
    """Constrói cabeçalho + dados, pronto a converter em bits."""
    flags = FLAG_ENCRYPTED if encrypted else 0
    header = _HEADER_STRUCT.pack(MAGIC, VERSION, flags, len(data), zlib.crc32(data))
    return header + data


def parse_header(raw: bytes, max_data_bytes: int) -> Header:
    """Valida os 14 bytes do cabeçalho.

    ``max_data_bytes`` é o máximo que a imagem consegue conter depois do
    cabeçalho; um comprimento acima disso indica payload truncado/corrompido.
    """
    if len(raw) < HEADER_SIZE:
        raise NoPayloadError("A imagem é demasiado pequena para conter uma mensagem.")

    magic, version, flags, length, crc = _HEADER_STRUCT.unpack(raw[:HEADER_SIZE])

    if magic != MAGIC:
        raise NoPayloadError(
            "Não foi encontrada nenhuma mensagem StegoLab nesta imagem."
        )
    if version != VERSION:
        raise CorruptPayloadError(
            f"Versão de payload não suportada ({version})."
        )
    if flags & ~KNOWN_FLAGS:
        raise CorruptPayloadError("O cabeçalho contém indicadores desconhecidos.")
    if length == 0:
        raise CorruptPayloadError("O cabeçalho indica uma mensagem vazia.")
    if length > max_data_bytes or length > MAX_DATA_BYTES:
        raise CorruptPayloadError(
            "O comprimento indicado no cabeçalho excede a capacidade da imagem: "
            "o payload está truncado ou corrompido."
        )
    return Header(version=version, flags=flags, length=length, crc32=crc)


def verify_data(header: Header, data: bytes) -> None:
    """Confirma que os dados extraídos correspondem ao CRC32 do cabeçalho."""
    if len(data) != header.length or zlib.crc32(data) != header.crc32:
        raise CorruptPayloadError(
            "A mensagem foi encontrada, mas os dados estão corrompidos "
            "(a imagem pode ter sido editada, redimensionada ou comprimida)."
        )


# --------------------------------------------------------------------------
# Conversão bytes <-> bits (do bit mais significativo para o menos)
# --------------------------------------------------------------------------

def bytes_to_bits(data: bytes) -> list[int]:
    """b"A" (0x41) -> [0, 1, 0, 0, 0, 0, 0, 1]"""
    bits: list[int] = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits


def bits_to_bytes(bits: list[int]) -> bytes:
    """[0, 1, 0, 0, 0, 0, 0, 1] -> b"A" (ignora bits que não completem um byte)."""
    out = bytearray()
    for i in range(0, len(bits) - len(bits) % 8, 8):
        byte = 0
        for bit in bits[i : i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes(out)
