"""Codificação LSB: esconder uma mensagem nos bits menos significativos.

Exemplo para um canal de cor com valor 200 e o bit da mensagem igual a 1:

    200 = 1100100[0]  ->  limpar o LSB  (& 0xFE) -> 1100100[0]
                      ->  escrever o bit (| 1)   -> 1100100[1] = 201

A cor muda no máximo 1 unidade em 255, o que é imperceptível à vista.
"""

from __future__ import annotations

from PIL import Image

from . import crypto
from .errors import CapacityError, EmptyMessageError, MessageTooLongError
from .image_utils import capacity_bytes, merge_channels, split_channels
from .payload import HEADER_SIZE, build_payload, bytes_to_bits

MAX_MESSAGE_BYTES = 100_000  # limite razoável para uma demonstração


def embed_bits(carrier: bytearray, bits: list[int]) -> None:
    """Escreve cada bit no LSB de um byte de cor (R, G, B, R, G, B, ...).

    Altera ``carrier`` no próprio objecto. Nunca escreve além do seu tamanho.
    """
    if len(bits) > len(carrier):
        raise CapacityError("Não existem canais de cor suficientes para os dados.")
    for i, bit in enumerate(bits):
        carrier[i] = (carrier[i] & 0xFE) | bit


def prepare_data(message: str, password: str | None = None) -> tuple[bytes, bool]:
    """Valida e converte a mensagem em bytes (UTF-8), encriptando-a se pedido."""
    if not isinstance(message, str) or message.strip() == "":
        raise EmptyMessageError("Escreva uma mensagem antes de a esconder.")
    data = message.encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise MessageTooLongError(
            f"A mensagem tem {len(data):,} bytes; o máximo permitido é "
            f"{MAX_MESSAGE_BYTES:,} bytes."
        )
    if password:
        return crypto.encrypt(data, password), True
    return data, False


def required_bytes(message: str, encrypted: bool = False) -> int:
    """Bytes que a mensagem ocupará na imagem (cabeçalho incluído)."""
    size = len(message.encode("utf-8"))
    if encrypted:
        size = crypto.encrypted_size(size)
    return HEADER_SIZE + size


def hide_message(
    image: Image.Image, message: str, password: str | None = None
) -> Image.Image:
    """Devolve uma NOVA imagem com a mensagem escondida.

    A imagem original nunca é modificada; as dimensões são preservadas.
    """
    data, encrypted = prepare_data(message, password)

    available = capacity_bytes(image)
    if len(data) > available:
        raise CapacityError(
            f"A mensagem precisa de {len(data):,} bytes, mas a imagem só suporta "
            f"{available:,} bytes. Use uma imagem maior ou uma mensagem mais curta."
        )

    rgb, alpha = split_channels(image)  # convert() cria cópias
    carrier = bytearray(rgb.tobytes())  # R,G,B,R,G,B,... linha a linha
    embed_bits(carrier, bytes_to_bits(build_payload(data, encrypted)))

    stego_rgb = Image.frombytes("RGB", rgb.size, bytes(carrier))
    return merge_channels(stego_rgb, alpha)
