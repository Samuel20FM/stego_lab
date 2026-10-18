"""Vídeo: LSB nas amostras da faixa de áudio (requer FFmpeg).

Esconder bits nos píxeis de cada fotograma obrigaria a gravar o vídeo inteiro
sem perdas: um clipe de 10 s em 720p passaria de ~5 MB para ~130 MB. Em vez
disso, o StegoLab:

1. copia o fluxo de vídeo tal como está (sem recodificar, sem perda de qualidade);
2. descodifica a faixa de áudio para PCM de 16 bits (sem perdas a partir daqui);
3. escreve o payload nos LSB dessas amostras, como num WAV;
4. junta vídeo + áudio PCM num ficheiro Matroska (.mkv).

Se o vídeo não tiver som, é criada uma faixa silenciosa. Converter o resultado
para MP4/AAC, ou enviá-lo por redes sociais, recomprime o áudio e destrói a
mensagem.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from functools import cached_property
from pathlib import Path

from PIL import Image

from ..errors import CapacityError, InvalidFileError, ToolMissingError
from .audio import fmt_channels, fmt_duration
from .base import LsbCarrier, Output

VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB (entrada e resultado)
SILENT_RATE = 48_000
SILENT_CHANNELS = 2
TIMEOUT = 180  # segundos por chamada ao FFmpeg

# Demultiplexadores permitidos, escolhidos pela assinatura do ficheiro. O
# formato é sempre imposto ao FFmpeg (-f) para que um ficheiro malicioso não
# consiga activar outro demultiplexador (por ex., listas HLS dentro de AVI).
MP4_DEMUXER = "mov"
MKV_DEMUXER = "matroska"


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def sniff_video(head: bytes) -> str | None:
    if head[4:8] == b"ftyp":
        return MP4_DEMUXER
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return MKV_DEMUXER
    return None


def _run(args: list[str], stdin: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(
            args, input=stdin, capture_output=True, timeout=TIMEOUT, check=False
        )
    except subprocess.TimeoutExpired:
        raise InvalidFileError("O processamento do vídeo demorou demasiado tempo.") from None
    if proc.returncode != 0:
        raise InvalidFileError(
            "O FFmpeg não conseguiu processar o vídeo: o ficheiro pode estar danificado."
        )
    return proc.stdout


class VideoCarrier(LsbCarrier):
    kind = "video"
    label = "Vídeo"
    technique = "LSB nas amostras da faixa de áudio"

    def __init__(self, data: bytes, filename: str = "") -> None:
        super().__init__(data, filename)
        if not ffmpeg_available():
            raise ToolMissingError(
                "O suporte a vídeo precisa do FFmpeg instalado (veja o README)."
            )
        demuxer = sniff_video(data[:16])
        if demuxer is None:
            raise InvalidFileError("Formato de vídeo não suportado. Use MP4, MOV, MKV ou WebM.")
        self.demuxer = demuxer
        self._probe()

    # ------------------------------------------------------------------ FFmpeg

    def _with_input(self, func):
        """Grava o vídeo num ficheiro temporário (o FFmpeg precisa de procurar)."""
        with tempfile.TemporaryDirectory(prefix="stegolab_") as tmp:
            path = Path(tmp) / "entrada"
            path.write_bytes(self.data)
            return func(Path(tmp), str(path))

    def _input_args(self, path: str) -> list[str]:
        return ["-f", self.demuxer, "-i", path]

    def _probe(self) -> None:
        def probe(_tmp: Path, path: str) -> dict:
            out = _run(
                ["ffprobe", "-v", "error", "-f", self.demuxer,
                 "-show_entries",
                 "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels"
                 ":stream_disposition=attached_pic:format=duration",
                 "-of", "json", path]
            )
            return json.loads(out or b"{}")

        info = self._with_input(probe)
        streams = info.get("streams", [])
        video = next(
            (s for s in streams if s.get("codec_type") == "video"
             and not s.get("disposition", {}).get("attached_pic")),
            None,
        )
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        if video is None:
            raise InvalidFileError(
                "Não foi encontrada nenhuma faixa de vídeo. Para áudio, use um ficheiro WAV."
            )
        try:
            self.duration = float(info.get("format", {}).get("duration") or 0)
        except ValueError:
            self.duration = 0.0
        if self.duration <= 0:
            raise InvalidFileError("Não foi possível determinar a duração do vídeo.")

        self.width = int(video.get("width") or 0)
        self.height = int(video.get("height") or 0)
        self.video_codec = video.get("codec_name", "?")
        num, _, den = str(video.get("avg_frame_rate", "0/1")).partition("/")
        self.fps = float(num) / float(den) if den and float(den) else 0.0
        self.has_audio = audio is not None
        if audio is not None:
            self.audio_codec = audio.get("codec_name", "?")
            self.sample_rate = int(audio.get("sample_rate") or 0)
            self.channels = int(audio.get("channels") or 0)
            if not self.sample_rate or not self.channels:
                raise InvalidFileError("A faixa de áudio do vídeo não é válida.")
        else:
            self.audio_codec = None
            self.sample_rate, self.channels = SILENT_RATE, SILENT_CHANNELS

    @cached_property
    def _pcm(self) -> bytes:
        """Áudio em PCM de 16 bits (little-endian), intercalado por canal."""
        if not self.has_audio:
            frames = round(self.duration * SILENT_RATE)
            return bytes(frames * SILENT_CHANNELS * 2)
        return self._with_input(
            lambda _tmp, path: _run(
                ["ffmpeg", "-nostdin", "-v", "error", *self._input_args(path),
                 "-map", "0:a:0", "-vn", "-sn", "-dn",
                 "-c:a", "pcm_s16le", "-f", "s16le", "-"]
            )
        )

    @cached_property
    def first_frame(self) -> Image.Image:
        png = self._with_input(
            lambda _tmp, path: _run(
                ["ffmpeg", "-nostdin", "-v", "error", *self._input_args(path),
                 "-map", "0:v:0", "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"]
            )
        )
        import io

        img = Image.open(io.BytesIO(png))
        img.load()
        return img

    # --------------------------------------------------------------------- LSB

    def slots(self) -> bytes:
        return self._pcm[0::2]  # byte baixo de cada amostra de 16 bits

    @property
    def estimated_output(self) -> int:
        return self.size + round(self.duration * self.sample_rate) * self.channels * 2

    def rebuild(self, slots: bytes, fmt: str | None = None) -> Output:
        if self.estimated_output > VIDEO_MAX_BYTES:
            raise CapacityError(
                "O vídeo resultante excederia 100 MB (o áudio passa a PCM sem perdas). "
                "Use um vídeo mais curto."
            )
        pcm = bytearray(self._pcm)
        pcm[0::2] = slots

        def mux(tmp: Path, path: str) -> bytes:
            raw = tmp / "audio.pcm"
            out = tmp / "saida.mkv"
            raw.write_bytes(bytes(pcm))
            _run(
                ["ffmpeg", "-nostdin", "-v", "error", "-y", *self._input_args(path),
                 "-f", "s16le", "-ar", str(self.sample_rate), "-ac", str(self.channels),
                 "-i", str(raw),
                 "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "pcm_s16le",
                 "-map_metadata", "0", "-f", "matroska", str(out)]
            )
            return out.read_bytes()

        return Output(self._with_input(mux), "mkv", "video/x-matroska")

    def details(self) -> list[tuple[str, str]]:
        audio = (
            f"{self.audio_codec.upper()} · {self.sample_rate:,} Hz".replace(",", " ")
            if self.has_audio
            else "sem som (será criada uma faixa silenciosa)"
        )
        return [
            ("Resolução", f"{self.width}×{self.height}"),
            ("Duração", fmt_duration(self.duration)),
            ("Codec de vídeo", self.video_codec.upper()),
            ("Áudio", audio),
            ("Canais", fmt_channels(self.channels)),
        ]
