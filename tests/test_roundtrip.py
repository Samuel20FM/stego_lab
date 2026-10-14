"""Testes de ida e volta: esconder -> gravar -> reabrir -> extrair."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from conftest import ROOT, make_image, to_bytes
from steganography import (
    OUTPUT_FORMATS,
    capacity_bytes,
    hide_message,
    image_to_bytes,
    load_image,
    reveal_message,
    save_image,
)


def _roundtrip(img, message, fmt="PNG", password=None):
    stego = hide_message(img, message, password=password)
    reopened, _ = load_image(image_to_bytes(stego, fmt))
    return reveal_message(reopened, password=password)


def test_simple_message(rgb_image):
    result = _roundtrip(rgb_image, "Hello, StegoLab!")
    assert result.message == "Hello, StegoLab!"
    assert result.encrypted is False


def test_portuguese_accents(rgb_image):
    msg = "Informação secreta: avó, coração, não, pêssego, ação, à, Moçambique."
    assert _roundtrip(rgb_image, msg).message == msg


def test_unicode_and_special_characters(rgb_image):
    msg = "Emoji 🔐🛰️ · 中文 · العربية · Ελληνικά · ∑∞≠ · <tag> & \"aspas\" \n\t fim"
    assert _roundtrip(rgb_image, msg).message == msg


def test_long_message_fills_image(big_image):
    msg = ("Universidade Pedagógica de Maputo — Segurança Informática. " * 2000)
    msg = msg.encode("utf-8")[: capacity_bytes(big_image)].decode("utf-8", "ignore")
    assert _roundtrip(big_image, msg).message == msg


@pytest.mark.parametrize("fmt", sorted(OUTPUT_FORMATS))
def test_every_output_format_is_lossless(rgb_image, fmt):
    msg = f"formato {fmt} sem perdas ✓"
    assert _roundtrip(rgb_image, msg, fmt=fmt).message == msg


@pytest.mark.parametrize("fmt", sorted(OUTPUT_FORMATS))
def test_rgba_roundtrip_in_every_format(fmt):
    img = make_image(40, 40, mode="RGBA", seed=5)
    msg = "com canal alfa"
    assert _roundtrip(img, msg, fmt=fmt).message == msg


@pytest.mark.parametrize("mode", ["L", "P", "LA"])
def test_other_colour_modes(mode):
    img = make_image(40, 40).convert(mode)
    assert _roundtrip(img, "modo " + mode).message == "modo " + mode


def test_bmp_input_and_jpeg_input_produce_valid_png(rgb_image):
    for fmt in ("BMP", "JPEG"):
        carrier, _ = load_image(to_bytes(rgb_image, fmt))
        assert _roundtrip(carrier, f"entrada {fmt}").message == f"entrada {fmt}"


def test_encrypted_roundtrip(rgb_image):
    result = _roundtrip(rgb_image, "Encontro às 15h na biblioteca.", password="UP-Maputo")
    assert result.message == "Encontro às 15h na biblioteca."
    assert result.encrypted is True


def test_file_on_disk_roundtrip(tmp_path, rgb_image):
    path = save_image(hide_message(rgb_image, "guardado em disco"), tmp_path / "out.png")
    img, info = load_image(path)
    assert info.format == "PNG"
    assert reveal_message(img).message == "guardado em disco"


def test_extraction_works_in_a_separate_process(tmp_path, rgb_image):
    """Simula fechar e reabrir a aplicação: outro interpretador Python extrai."""
    msg = "Sobrevive ao reinício — ç ã é 🔑"
    path = save_image(hide_message(rgb_image, msg, password="pw"), tmp_path / "stego.png")
    script = textwrap.dedent(
        """
        import sys
        from steganography import load_image, reveal_message
        img, _ = load_image(sys.argv[1])
        sys.stdout.buffer.write(reveal_message(img, password="pw").message.encode("utf-8"))
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    assert out.stdout.decode("utf-8") == msg
