"""Áudio WAV (PCM): LSB no byte menos significativo de cada amostra.

Num WAV de 16 bits, cada amostra ocupa 2 bytes em little-endian; o primeiro
byte contém o bit menos significativo. Alterá-lo muda a amplitude em ±1 num
intervalo de 65 536 valores: muito abaixo do que o ouvido consegue notar.
"""

from __future__ import annotations

import io
import wave
from functools import cached_property

from ..errors import InvalidFileError
from .base import LsbCarrier, Output


def fmt_duration(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    text = f"{int(minutes)} min {secs:04.1f} s" if minutes else f"{secs:.1f} s"
    return text.replace(".", ",")


def fmt_channels(n: int) -> str:
    return {1: "1 (mono)", 2: "2 (estéreo)"}.get(n, str(n))


class WavCarrier(LsbCarrier):
    kind = "audio"
    label = "Áudio WAV"
    technique = "LSB nas amostras de som"

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        try:
            with wave.open(io.BytesIO(data), "rb") as w:
                self.params = w.getparams()
                self.frames = w.readframes(w.getnframes())
        except Exception:
            raise InvalidFileError(
                "O ficheiro WAV não é válido ou não usa PCM inteiro "
                "(o único tipo de WAV suportado)."
            ) from None
        p = self.params
        if p.sampwidth not in (1, 2, 3, 4) or p.nframes == 0:
            raise InvalidFileError("O ficheiro WAV não contém amostras de áudio utilizáveis.")
        if len(self.frames) != p.nframes * p.nchannels * p.sampwidth:
            raise InvalidFileError("O ficheiro WAV está truncado.")

    @cached_property
    def _slots(self) -> bytes:
        # Byte menos significativo de cada amostra (little-endian).
        return self.frames[0 :: self.params.sampwidth]

    def slots(self) -> bytes:
        return self._slots

    def rebuild(self, slots: bytes, fmt: str | None = None) -> Output:
        frames = bytearray(self.frames)
        frames[0 :: self.params.sampwidth] = slots
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setparams(self.params)
            w.writeframes(bytes(frames))
        return Output(buf.getvalue(), "wav", "audio/wav")

    @property
    def duration(self) -> float:
        return self.params.nframes / self.params.framerate

    def details(self) -> list[tuple[str, str]]:
        p = self.params
        return [
            ("Duração", fmt_duration(self.duration)),
            ("Canais", fmt_channels(p.nchannels)),
            ("Amostragem", f"{p.framerate:,} Hz".replace(",", " ")),
            ("Resolução", f"{p.sampwidth * 8} bits"),
        ]
