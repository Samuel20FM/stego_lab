"""Testes da extracção: imagens sem payload, truncadas, corrompidas e encriptadas."""

from __future__ import annotations

import io
import struct

import pytest
from PIL import Image

from conftest import make_image, to_bytes
from steganography import (
    CorruptPayloadError,
    NoPayloadError,
    PasswordRequiredError,
    WrongPasswordError,
    hide_message,
    load_image,
    read_header,
    reveal_message,
)
from steganography.encoder import embed_bits
from steganography.payload import MAGIC, bytes_to_bits


def _image_with_raw_payload(raw: bytes, size=(64, 48)) -> Image.Image:
    """Escreve bytes arbitrários nos LSB (para simular payloads inválidos)."""
    img = make_image(*size)
    carrier = bytearray(img.tobytes())
    embed_bits(carrier, bytes_to_bits(raw))
    return Image.frombytes("RGB", img.size, bytes(carrier))


def _header(length: int, crc: int = 0, version: int = 1, flags: int = 0) -> bytes:
    return struct.pack(">4sBBII", MAGIC, version, flags, length, crc)


def test_image_without_payload_is_detected(rgb_image):
    with pytest.raises(NoPayloadError):
        reveal_message(rgb_image)
    with pytest.raises(NoPayloadError):
        read_header(rgb_image)


def test_plain_white_image_has_no_payload():
    with pytest.raises(NoPayloadError):
        reveal_message(Image.new("RGB", (50, 50), "white"))


def test_length_larger_than_capacity_is_rejected():
    img = _image_with_raw_payload(_header(length=10_000_000))
    with pytest.raises(CorruptPayloadError):
        reveal_message(img)


def test_zero_length_is_rejected():
    with pytest.raises(CorruptPayloadError):
        reveal_message(_image_with_raw_payload(_header(length=0)))


def test_unknown_version_is_rejected():
    with pytest.raises(CorruptPayloadError):
        reveal_message(_image_with_raw_payload(_header(length=5, version=9)))


def test_unknown_flags_are_rejected():
    with pytest.raises(CorruptPayloadError):
        reveal_message(_image_with_raw_payload(_header(length=5, flags=0b1000_0000)))


def test_truncated_payload_after_crop_is_rejected(big_image):
    stego = hide_message(big_image, "mensagem longa " * 200)
    cropped = stego.crop((0, 0, 40, 40))  # capacidade muito menor
    with pytest.raises(CorruptPayloadError):
        reveal_message(cropped)


def test_corrupted_data_fails_crc(rgb_image):
    stego = hide_message(rgb_image, "integridade verificada por CRC32")
    carrier = bytearray(stego.tobytes())
    carrier[14 * 8 + 3] ^= 1  # inverte um bit dentro dos dados
    tampered = Image.frombytes("RGB", stego.size, bytes(carrier))
    with pytest.raises(CorruptPayloadError):
        reveal_message(tampered)


def test_jpeg_compression_destroys_payload(big_image):
    stego = hide_message(big_image, "a compressão com perdas destrói o payload")
    jpeg, _ = load_image(to_bytes(stego, "JPEG", quality=95))
    with pytest.raises((NoPayloadError, CorruptPayloadError)):
        reveal_message(jpeg)


def test_encrypted_flag_is_detected(rgb_image):
    assert read_header(hide_message(rgb_image, "aberta")).encrypted is False
    assert read_header(hide_message(rgb_image, "fechada", password="pw")).encrypted is True


def test_encrypted_payload_requires_password(rgb_image):
    stego = hide_message(rgb_image, "precisa de senha", password="Moz2026")
    with pytest.raises(PasswordRequiredError):
        reveal_message(stego)


def test_wrong_password_is_rejected(rgb_image):
    stego = hide_message(rgb_image, "senha errada", password="correcta")
    with pytest.raises(WrongPasswordError):
        reveal_message(stego, password="errada")


def test_encrypted_payload_does_not_contain_plaintext(rgb_image):
    secret = "texto-que-nao-deve-aparecer"
    stego = hide_message(rgb_image, secret, password="pw")
    carrier = stego.tobytes()
    from steganography.payload import bits_to_bytes

    lsb_bytes = bits_to_bytes([b & 1 for b in carrier])
    assert secret.encode() not in lsb_bytes


def test_unencrypted_payload_ignores_password(rgb_image):
    stego = hide_message(rgb_image, "sem encriptação")
    assert reveal_message(stego, password="qualquer").message == "sem encriptação"
