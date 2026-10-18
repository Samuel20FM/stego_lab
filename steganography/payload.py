"""Formato do payload e conversão entre bytes e bits.

Estrutura do payload escondido na imagem (14 bytes de cabeçalho + dados):

    +--------+---------+-------+-------------+-----------+-------------+
    | MAGIC  | VERSÃO  | FLAGS | COMPRIMENTO | CRC32     | DADOS       |
    | 4 B    | 1 B     | 1 B   | 4 B (BE)    | 4 B (BE)  | N bytes     |
    | "STGL" | 0x01    | bit0= | N           | dos DADOS | mensagem    |
    |        |         | encr. |             |           | (ou cifra)  |
    |        |         | bit1= |             |           |             |
    |        |         | meta  |             |           |             |
    +--------+---------+-------+-------------+-----------+-------------+

* MAGIC identifica ficheiros produzidos pelo StegoLab.
* COMPRIMENTO diz exactamente quantos bytes ler — nunca lemos "a imagem toda".
* CRC32 detecta dados truncados ou alterados (por ex., compressão JPEG).

Quando o segredo é um ficheiro ou tem data de validade, o indicador META está
activo e os dados (antes de qualquer encriptação) começam com um bloco extra:

    TIPO (1 B: 0 = texto, 1 = ficheiro) | VALIDADE (8 B, Unix; 0 = sem) |
    COMPRIMENTO DO NOME (1 B) | NOME (UTF-8) | CONTEÚDO

Uma mensagem de texto simples, sem validade, não usa este bloco: o formato é
exactamente o da primeira versão do StegoLab.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from .errors import CorruptPayloadError, NoPayloadError

MAGIC = b"STGL"
VERSION = 1
FLAG_ENCRYPTED = 0b0000_0001
FLAG_META = 0b0000_0010
KNOWN_FLAGS = FLAG_ENCRYPTED | FLAG_META

# ">4sBBII": magic (4s), versão (B), flags (B), comprimento (I), crc32 (I)
_HEADER_STRUCT = struct.Struct(">4sBBII")
HEADER_SIZE = _HEADER_STRUCT.size  # 14 bytes
HEADER_BITS = HEADER_SIZE * 8  # 112 bits

# Limite de segurança para os dados (após encriptação, se existir).
MAX_DATA_BYTES = 2 * 1024 * 1024

KIND_TEXT = 0
KIND_FILE = 1
# ">BQB": tipo (B), validade (Q), comprimento do nome (B)
_META_STRUCT = struct.Struct(">BQB")
META_SIZE = _META_STRUCT.size  # 10 bytes + nome


@dataclass(frozen=True)
class Header:
    version: int
    flags: int
    length: int
    crc32: int

    @property
    def encrypted(self) -> bool:
        return bool(self.flags & FLAG_ENCRYPTED)

    @property
    def has_meta(self) -> bool:
        return bool(self.flags & FLAG_META)


def build_payload(data: bytes, encrypted: bool = False, meta: bool = False) -> bytes:
    """Constrói cabeçalho + dados, pronto a converter em bits."""
    flags = (FLAG_ENCRYPTED if encrypted else 0) | (FLAG_META if meta else 0)
    header = _HEADER_STRUCT.pack(MAGIC, VERSION, flags, len(data), zlib.crc32(data))
    return header + data


def parse_header(raw: bytes, max_data_bytes: int) -> Header:
    """Valida os 14 bytes do cabeçalho.

    ``max_data_bytes`` é o máximo que a imagem consegue conter depois do
    cabeçalho; um comprimento acima disso indica payload truncado/corrompido.
    """
    if len(raw) < HEADER_SIZE:
        raise NoPayloadError("O ficheiro é demasiado pequeno para conter uma mensagem.")

    magic, version, flags, length, crc = _HEADER_STRUCT.unpack(raw[:HEADER_SIZE])

    if magic != MAGIC:
        raise NoPayloadError(
            "Não foi encontrada nenhuma mensagem StegoLab neste ficheiro."
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
            "O comprimento indicado no cabeçalho excede a capacidade do ficheiro: "
            "o payload está truncado ou corrompido."
        )
    return Header(version=version, flags=flags, length=length, crc32=crc)


def split_payload(raw: bytes) -> tuple[Header, bytes]:
    """Separa cabeçalho e dados quando o payload já está em bytes (texto, PDF, ZIP)."""
    header = parse_header(raw[:HEADER_SIZE], max(0, len(raw) - HEADER_SIZE))
    return header, raw[HEADER_SIZE : HEADER_SIZE + header.length]


def verify_data(header: Header, data: bytes) -> None:
    """Confirma que os dados extraídos correspondem ao CRC32 do cabeçalho."""
    if len(data) != header.length or zlib.crc32(data) != header.crc32:
        raise CorruptPayloadError(
            "A mensagem foi encontrada, mas os dados estão corrompidos "
            "(o ficheiro pode ter sido editado, convertido ou comprimido)."
        )


def pack_meta(kind: int, expires_at: int | None, name: str | None) -> bytes:
    raw_name = (name or "").encode("utf-8")
    return _META_STRUCT.pack(kind, expires_at or 0, len(raw_name)) + raw_name


def unpack_meta(data: bytes) -> tuple[int, int | None, str | None, bytes]:
    """Devolve (tipo, validade, nome, conteúdo)."""
    if len(data) < META_SIZE:
        raise CorruptPayloadError("O bloco de metadados está incompleto.")
    kind, expires_at, name_len = _META_STRUCT.unpack(data[:META_SIZE])
    if kind not in (KIND_TEXT, KIND_FILE) or len(data) < META_SIZE + name_len:
        raise CorruptPayloadError("O bloco de metadados é inválido.")
    try:
        name = data[META_SIZE : META_SIZE + name_len].decode("utf-8") or None
    except UnicodeDecodeError:
        raise CorruptPayloadError("O nome do ficheiro escondido é inválido.") from None
    return kind, expires_at or None, name, data[META_SIZE + name_len :]


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
