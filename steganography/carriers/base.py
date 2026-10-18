"""Interface comum a todos os ficheiros de cobertura ("portadores")."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePath

from ..decoder import read_lsb_header, read_lsb_payload
from ..encoder import embed_payload
from ..payload import HEADER_SIZE, MAX_DATA_BYTES, Header


@dataclass(frozen=True)
class Output:
    """Ficheiro gerado: bytes, extensão e tipo MIME para o download."""

    data: bytes
    ext: str
    mime: str


class Carrier(ABC):
    """Um ficheiro de cobertura já validado pelo conteúdo.

    Os objectos são tratados como imutáveis: ``embed`` devolve sempre um
    ficheiro novo e nunca altera ``data``.
    """

    kind: str = ""  # image | audio | video | text | pdf | zip
    label: str = ""
    technique: str = ""
    lsb: bool = False  # True quando a técnica é LSB
    output_formats: tuple[str, ...] = ()

    def __init__(self, data: bytes, filename: str = "") -> None:
        self.data = data
        self.filename = filename

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def stem(self) -> str:
        return PurePath(self.filename).stem or "ficheiro"

    @abstractmethod
    def capacity(self) -> int:
        """Bytes de dados que cabem no portador (sem o cabeçalho de 14 bytes)."""

    @abstractmethod
    def embed(self, payload: bytes, fmt: str | None = None) -> Output:
        """Devolve um NOVO ficheiro com o payload (cabeçalho + dados)."""

    @abstractmethod
    def extract(self) -> tuple[Header, bytes]:
        """Lê o cabeçalho e os dados escondidos."""

    def read_header(self) -> Header:
        return self.extract()[0]

    def details(self) -> list[tuple[str, str]]:
        return []


class LsbCarrier(Carrier):
    """Portador em que cada byte de ``slots()`` guarda um bit no seu LSB."""

    lsb = True

    @abstractmethod
    def slots(self) -> bytes:
        """Bytes portadores: canais de cor, ou o byte baixo de cada amostra."""

    @abstractmethod
    def rebuild(self, slots: bytes, fmt: str | None = None) -> Output:
        """Reconstrói o ficheiro a partir dos bytes portadores alterados."""

    def capacity(self) -> int:
        return max(0, min(len(self.slots()) // 8 - HEADER_SIZE, MAX_DATA_BYTES))

    def embed(self, payload: bytes, fmt: str | None = None) -> Output:
        carrier = bytearray(self.slots())
        embed_payload(carrier, payload)
        return self.rebuild(bytes(carrier), fmt)

    def extract(self) -> tuple[Header, bytes]:
        return read_lsb_payload(self.slots())

    def read_header(self) -> Header:
        return read_lsb_header(self.slots())
