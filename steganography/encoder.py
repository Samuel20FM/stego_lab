"""Codificação LSB: esconder uma mensagem nos bits menos significativos.

Exemplo para um canal de cor com valor 200 e o bit da mensagem igual a 1:

    200 = 1100100[0]  ->  limpar o LSB  (& 0xFE) -> 1100100[0]
                      ->  escrever o bit (| 1)   -> 1100100[1] = 201

A cor muda no máximo 1 unidade em 255, o que é imperceptível à vista. O mesmo
princípio aplica-se às amostras de áudio (WAV e faixa de som dos vídeos).
"""

from __future__ import annotations

from PIL import Image

from .errors import CapacityError
from .image_utils import capacity_bytes, merge_channels, split_channels
from .payload import HEADER_SIZE, bytes_to_bits
from .secret import MAX_MESSAGE_BYTES, Secret, estimate_size, make_payload

__all__ = [
    "MAX_MESSAGE_BYTES",
    "embed_bits",
    "embed_payload",
    "embed_payload_in_image",
    "hide_message",
    "required_bytes",
]


def embed_bits(carrier: bytearray, bits: list[int]) -> None:
    """Escreve cada bit no LSB de um byte portador (R, G, B, R, G, B, ...).

    Altera ``carrier`` no próprio objecto. Nunca escreve além do seu tamanho.
    """
    if len(bits) > len(carrier):
        raise CapacityError("Não existem bytes portadores suficientes para os dados.")
    for i, bit in enumerate(bits):
        carrier[i] = (carrier[i] & 0xFE) | bit


def embed_payload(carrier: bytearray, payload: bytes) -> None:
    """Escreve o payload completo (cabeçalho + dados) a partir do início."""
    available = len(carrier) // 8 - HEADER_SIZE
    needed = len(payload) - HEADER_SIZE
    if needed > available:
        raise CapacityError(
            f"O segredo precisa de {needed:,} bytes, mas o ficheiro só suporta "
            f"{max(0, available):,} bytes. Use um ficheiro maior ou um segredo mais pequeno."
        )
    embed_bits(carrier, bytes_to_bits(payload))


def required_bytes(message: str, encrypted: bool = False) -> int:
    """Bytes que a mensagem ocupará no portador (cabeçalho incluído)."""
    return estimate_size(len(message.encode("utf-8")), encrypted=encrypted)


def embed_payload_in_image(image: Image.Image, payload: bytes) -> Image.Image:
    """Devolve uma NOVA imagem com o payload nos LSB dos canais R, G e B."""
    rgb, alpha = split_channels(image)  # convert() cria cópias
    carrier = bytearray(rgb.tobytes())  # R,G,B,R,G,B,... linha a linha
    embed_payload(carrier, payload)
    stego_rgb = Image.frombytes("RGB", rgb.size, bytes(carrier))
    return merge_channels(stego_rgb, alpha)


def hide_message(
    image: Image.Image, message: str, password: str | None = None
) -> Image.Image:
    """Devolve uma NOVA imagem com a mensagem escondida.

    A imagem original nunca é modificada; as dimensões são preservadas.
    """
    payload = make_payload(Secret.text(message), password)
    available = capacity_bytes(image)
    if len(payload) - HEADER_SIZE > available:
        raise CapacityError(
            f"A mensagem precisa de {len(payload) - HEADER_SIZE:,} bytes, mas a imagem só "
            f"suporta {available:,} bytes. Use uma imagem maior ou uma mensagem mais curta."
        )
    return embed_payload_in_image(image, payload)
