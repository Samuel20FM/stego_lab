"""Leitura, validação, capacidade e gravação de imagens (Pillow)."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Union

from PIL import Image, UnidentifiedImageError

from .errors import InvalidImageError
from .payload import HEADER_SIZE

ImageSource = Union[str, Path, bytes, BinaryIO]

# Formatos aceites como *entrada*. A validação usa o conteúdo do ficheiro
# (detectado pelo Pillow), nunca apenas a extensão.
INPUT_FORMATS = {"PNG", "BMP", "TIFF", "WEBP", "JPEG"}
# Formatos com perdas: servem como imagem de partida, mas não guardam payload.
LOSSY_FORMATS = {"JPEG"}

# Formatos de *saída* — todos sem perdas, para não destruir os bits LSB.
OUTPUT_FORMATS: dict[str, dict] = {
    "PNG": {"ext": "png", "mime": "image/png", "params": {"optimize": False}},
    "BMP": {"ext": "bmp", "mime": "image/bmp", "params": {}},
    "TIFF": {"ext": "tiff", "mime": "image/tiff", "params": {"compression": "tiff_lzw"}},
    "WEBP": {
        "ext": "webp",
        "mime": "image/webp",
        # exact=True preserva os valores RGB mesmo em píxeis transparentes
        "params": {"lossless": True, "quality": 100, "method": 4, "exact": True},
    },
}

MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_PIXELS = 40_000_000  # ~40 megapíxeis
MIN_SIDE = 8


@dataclass(frozen=True)
class ImageInfo:
    width: int
    height: int
    format: str
    mode: str
    file_size: int | None

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def lossy(self) -> bool:
        return self.format in LOSSY_FORMATS


def _read_source(source: ImageSource) -> bytes:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise InvalidImageError("O ficheiro indicado não existe.")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise InvalidImageError("O ficheiro excede o limite de 25 MB.")
        return path.read_bytes()
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    else:
        data = source.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise InvalidImageError("O ficheiro excede o limite de 25 MB.")
    return data


def load_image(source: ImageSource) -> tuple[Image.Image, ImageInfo]:
    """Abre e valida uma imagem a partir de um caminho, bytes ou ficheiro.

    Devolve a imagem já carregada em memória e os respectivos metadados.
    """
    data = _read_source(source)
    if not data:
        raise InvalidImageError("O ficheiro está vazio.")

    try:
        # 1.ª passagem: verifica a estrutura do ficheiro sem descodificar tudo.
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        # 2.ª passagem: verify() invalida o objecto, por isso reabrimos.
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            raise InvalidImageError(
                "A imagem é demasiado grande (máximo de 40 megapíxeis)."
            )
        img.load()
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError):
        raise InvalidImageError(
            "O ficheiro não é uma imagem válida ou o formato não é reconhecido."
        ) from None
    except Exception:  # ficheiro truncado, cabeçalho inválido, etc.
        raise InvalidImageError(
            "Não foi possível ler a imagem: o ficheiro pode estar danificado."
        ) from None

    if fmt not in INPUT_FORMATS:
        raise InvalidImageError(
            f"Formato '{fmt}' não suportado. Use PNG, BMP, TIFF, WEBP ou JPEG."
        )
    if min(img.size) < MIN_SIDE:
        raise InvalidImageError(f"A imagem tem de ter pelo menos {MIN_SIDE}×{MIN_SIDE} píxeis.")

    # Imagens animadas (GIF/WebP/TIFF multipágina): usa-se só o 1.º quadro.
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)
        img = img.copy()

    info = ImageInfo(img.width, img.height, fmt, img.mode, len(data))
    return img, info


def split_channels(img: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    """Converte para RGB e separa o canal alfa (transparência), se existir.

    Os bits são escondidos apenas em R, G e B; o alfa é preservado intacto.
    """
    has_alpha = img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        rgba = img.convert("RGBA")
        return rgba.convert("RGB"), rgba.getchannel("A")
    return img.convert("RGB"), None


def merge_channels(rgb: Image.Image, alpha: Image.Image | None) -> Image.Image:
    if alpha is None:
        return rgb
    out = rgb.copy()
    out.putalpha(alpha)
    return out


def capacity_bits(img: Image.Image) -> int:
    """1 bit por canal de cor (R, G, B) em cada píxel."""
    return img.width * img.height * 3


def capacity_bytes(img: Image.Image) -> int:
    """Bytes de dados disponíveis, já descontado o cabeçalho de 14 bytes."""
    return max(0, capacity_bits(img) // 8 - HEADER_SIZE)


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    """Grava a imagem num formato sem perdas e devolve os bytes."""
    fmt = fmt.upper()
    if fmt not in OUTPUT_FORMATS:
        raise ValueError(f"Formato de saída não suportado: {fmt}")
    buf = io.BytesIO()
    img.save(buf, format=fmt, **OUTPUT_FORMATS[fmt]["params"])
    return buf.getvalue()


def save_image(img: Image.Image, path: str | Path, fmt: str = "PNG") -> Path:
    path = Path(path)
    path.write_bytes(image_to_bytes(img, fmt))
    return path
