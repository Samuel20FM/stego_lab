"""Fixtures partilhadas: imagens geradas em memória (sem downloads)."""

from __future__ import annotations

import io
import random
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_image(width: int = 64, height: int = 48, mode: str = "RGB", seed: int = 1) -> Image.Image:
    """Imagem com ruído pseudo-aleatório reproduzível."""
    rng = random.Random(seed)
    channels = len(mode)  # "RGB" -> 3, "RGBA" -> 4, "L" -> 1
    data = bytes(rng.randrange(256) for _ in range(width * height * channels))
    return Image.frombytes(mode, (width, height), data)


def to_bytes(img: Image.Image, fmt: str = "PNG", **params) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **params)
    return buf.getvalue()


@pytest.fixture
def rgb_image() -> Image.Image:
    return make_image()


@pytest.fixture
def big_image() -> Image.Image:
    return make_image(400, 300, seed=7)
