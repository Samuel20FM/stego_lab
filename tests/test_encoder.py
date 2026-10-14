"""Testes da codificação, da validação de imagens e da capacidade."""

from __future__ import annotations

import pytest
from PIL import Image, ImageChops

from conftest import make_image, to_bytes
from steganography import (
    CapacityError,
    EmptyMessageError,
    InvalidImageError,
    MAX_MESSAGE_BYTES,
    MessageTooLongError,
    capacity_bytes,
    hide_message,
    load_image,
    required_bytes,
)
from steganography.encoder import embed_bits
from steganography.payload import HEADER_SIZE, bits_to_bytes, bytes_to_bits


def test_bits_conversion_is_reversible():
    data = "Olá, Maputo!".encode("utf-8")
    bits = bytes_to_bits(data)
    assert len(bits) == len(data) * 8
    assert bytes_to_bits(b"A") == [0, 1, 0, 0, 0, 0, 0, 1]
    assert bits_to_bytes(bits) == data


def test_embed_bits_only_changes_lsb():
    carrier = bytearray([200, 201, 0, 255])
    embed_bits(carrier, [1, 0, 1, 0])
    assert list(carrier) == [201, 200, 1, 254]


def test_preserves_dimensions(rgb_image):
    stego = hide_message(rgb_image, "dimensões")
    assert stego.size == rgb_image.size
    assert stego.mode == "RGB"


def test_original_image_is_not_modified(rgb_image):
    before = rgb_image.tobytes()
    hide_message(rgb_image, "não mexer no original")
    assert rgb_image.tobytes() == before


def test_pixel_values_change_at_most_by_one(rgb_image):
    stego = hide_message(rgb_image, "diferença máxima de 1")
    diff = ImageChops.difference(rgb_image, stego)
    assert max(hi for _, hi in diff.getextrema()) <= 1


def test_alpha_channel_is_preserved():
    img = make_image(32, 32, mode="RGBA", seed=3)
    stego = hide_message(img, "transparência")
    assert stego.mode == "RGBA"
    assert stego.getchannel("A").tobytes() == img.getchannel("A").tobytes()


def test_capacity_formula(rgb_image):
    # 64 x 48 píxeis x 3 canais = 9216 bits = 1152 bytes - 14 de cabeçalho
    assert capacity_bytes(rgb_image) == 64 * 48 * 3 // 8 - HEADER_SIZE


def test_message_that_exactly_fits_is_accepted(rgb_image):
    msg = "x" * capacity_bytes(rgb_image)
    assert required_bytes(msg) == capacity_bytes(rgb_image) + HEADER_SIZE
    hide_message(rgb_image, msg)


def test_rejects_message_over_capacity(rgb_image):
    msg = "x" * (capacity_bytes(rgb_image) + 1)
    with pytest.raises(CapacityError):
        hide_message(rgb_image, msg)


def test_rejects_message_over_capacity_when_encrypted(rgb_image):
    # Cabe em texto simples, mas não depois de encriptado (sal + token).
    msg = "x" * (capacity_bytes(rgb_image) - 10)
    with pytest.raises(CapacityError):
        hide_message(rgb_image, msg, password="segredo")


@pytest.mark.parametrize("message", ["", "   ", "\n\t"])
def test_rejects_empty_message(rgb_image, message):
    with pytest.raises(EmptyMessageError):
        hide_message(rgb_image, message)


def test_rejects_message_over_application_limit(big_image):
    with pytest.raises(MessageTooLongError):
        hide_message(big_image, "a" * (MAX_MESSAGE_BYTES + 1))


def test_load_image_accepts_png_and_bmp(rgb_image):
    for fmt in ("PNG", "BMP"):
        img, info = load_image(to_bytes(rgb_image, fmt))
        assert info.format == fmt
        assert img.size == (64, 48)
        assert info.file_size > 0


@pytest.mark.parametrize(
    "data",
    [b"", b"isto nao e uma imagem", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40],
    ids=["vazio", "texto", "png-truncado"],
)
def test_load_image_rejects_invalid_files(data):
    with pytest.raises(InvalidImageError):
        load_image(data)


def test_load_image_does_not_trust_extension(tmp_path):
    fake = tmp_path / "foto.png"
    fake.write_text("print('ola')")
    with pytest.raises(InvalidImageError):
        load_image(fake)


def test_load_image_rejects_unsupported_format(rgb_image):
    with pytest.raises(InvalidImageError):
        load_image(to_bytes(rgb_image, "GIF"))


def test_load_image_rejects_tiny_image():
    with pytest.raises(InvalidImageError):
        load_image(to_bytes(make_image(4, 4)))


def test_jpeg_is_flagged_as_lossy(rgb_image):
    _, info = load_image(to_bytes(rgb_image, "JPEG"))
    assert info.lossy
