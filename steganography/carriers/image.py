"""Imagens: LSB nos canais R, G e B (o portador original do StegoLab)."""

from __future__ import annotations

from functools import cached_property

from PIL import Image

from ..image_utils import OUTPUT_FORMATS, image_to_bytes, load_image, merge_channels, split_channels
from .base import LsbCarrier, Output


class ImageCarrier(LsbCarrier):
    kind = "image"
    label = "Imagem"
    technique = "LSB nos canais R, G e B"
    output_formats = tuple(OUTPUT_FORMATS)

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        self.image, self.info = load_image(data)

    @cached_property
    def _channels(self) -> tuple[Image.Image, Image.Image | None]:
        return split_channels(self.image)

    @cached_property
    def _slots(self) -> bytes:
        return self._channels[0].tobytes()  # R,G,B,R,G,B,... linha a linha

    def slots(self) -> bytes:
        return self._slots

    def rebuild(self, slots: bytes, fmt: str | None = None) -> Output:
        fmt = (fmt or "PNG").upper()
        rgb, alpha = self._channels
        stego = merge_channels(Image.frombytes("RGB", rgb.size, slots), alpha)
        spec = OUTPUT_FORMATS[fmt]
        return Output(image_to_bytes(stego, fmt), spec["ext"], spec["mime"])

    @property
    def lossy(self) -> bool:
        return self.info.lossy

    def details(self) -> list[tuple[str, str]]:
        return [
            ("Dimensões", f"{self.info.width}×{self.info.height}"),
            ("Formato", self.info.format),
            ("Modo", self.info.mode),
        ]
