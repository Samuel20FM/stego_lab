"""O segredo a esconder (texto ou ficheiro) e a sua preparação.

Esta camada é igual para todos os portadores (imagem, áudio, vídeo, texto,
PDF, Office): transforma o segredo nos bytes do payload e faz o inverso
depois da extracção — verificação do CRC32, desencriptação, metadados e
data de validade.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath

from . import crypto
from .errors import (
    CorruptPayloadError,
    EmptyMessageError,
    ExpiredMessageError,
    InvalidSecretError,
    MessageTooLongError,
    PasswordRequiredError,
)
from .payload import (
    HEADER_SIZE,
    KIND_FILE,
    KIND_TEXT,
    MAX_DATA_BYTES,
    META_SIZE,
    Header,
    build_payload,
    pack_meta,
    unpack_meta,
    verify_data,
)

MAX_MESSAGE_BYTES = 100_000  # limite razoável para uma mensagem de texto
MAX_SECRET_FILE_BYTES = MAX_DATA_BYTES - 4096  # margem para metadados e cifra
MAX_NAME_BYTES = 120


def format_datetime(ts: int) -> str:
    """Data/hora local legível: 18/10/2026 às 15:40."""
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y às %H:%M")


def safe_filename(name: str) -> str:
    """Remove caminhos e caracteres de controlo; limita o comprimento."""
    base = PurePath(name.replace("\\", "/")).name
    base = "".join(c for c in base if unicodedata.category(c)[0] != "C").strip(" .")
    raw = base.encode("utf-8")[:MAX_NAME_BYTES]
    return raw.decode("utf-8", "ignore") or "ficheiro"


@dataclass(frozen=True)
class Secret:
    """Texto ou ficheiro a esconder, com data de validade opcional (Unix, UTC)."""

    content: bytes
    filename: str | None = None  # None -> texto
    expires_at: int | None = None

    @classmethod
    def text(cls, message: str, expires_at: int | None = None) -> "Secret":
        if not isinstance(message, str) or message.strip() == "":
            raise EmptyMessageError("Escreva uma mensagem antes de a esconder.")
        data = message.encode("utf-8")
        if len(data) > MAX_MESSAGE_BYTES:
            raise MessageTooLongError(
                f"A mensagem tem {len(data):,} bytes; o máximo permitido é "
                f"{MAX_MESSAGE_BYTES:,} bytes."
            )
        return cls(data, None, expires_at)

    @classmethod
    def file(cls, name: str, data: bytes, expires_at: int | None = None) -> "Secret":
        if not data:
            raise EmptyMessageError("O ficheiro a esconder está vazio.")
        if len(data) > MAX_SECRET_FILE_BYTES:
            raise MessageTooLongError(
                f"O ficheiro tem {len(data):,} bytes; o máximo permitido é "
                f"{MAX_SECRET_FILE_BYTES:,} bytes."
            )
        return cls(bytes(data), safe_filename(name), expires_at)

    @property
    def is_file(self) -> bool:
        return self.filename is not None

    @property
    def message(self) -> str:
        if self.is_file:
            raise InvalidSecretError("O segredo é um ficheiro, não uma mensagem de texto.")
        return self.content.decode("utf-8")

    @property
    def needs_meta(self) -> bool:
        return self.is_file or self.expires_at is not None


def _plain_data(secret: Secret) -> bytes:
    if not secret.needs_meta:
        return secret.content  # formato original: só o texto em UTF-8
    kind = KIND_FILE if secret.is_file else KIND_TEXT
    return pack_meta(kind, secret.expires_at, secret.filename) + secret.content


def estimate_size(
    content_bytes: int,
    *,
    filename: str | None = None,
    expires: bool = False,
    encrypted: bool = False,
) -> int:
    """Bytes que o payload ocupará (cabeçalho incluído), sem o construir."""
    size = content_bytes
    if filename is not None or expires:
        size += META_SIZE + len(safe_filename(filename).encode("utf-8") if filename else b"")
    if encrypted:
        size = crypto.encrypted_size(size)
    return HEADER_SIZE + size


def max_secret_file(capacity: int, *, encrypted: bool = False, filename: str | None = None) -> int:
    """Maior ficheiro (em bytes) que cabe em ``capacity`` bytes de dados do portador.

    É o inverso de ``estimate_size``: conta com o bloco de metadados (nome do
    ficheiro) e, se houver palavra-passe, com a sobrecarga da encriptação.
    """
    def fits(n: int) -> bool:
        return estimate_size(n, filename=filename or "", encrypted=encrypted) - HEADER_SIZE <= capacity

    lo, hi = 0, MAX_SECRET_FILE_BYTES
    if not fits(0):
        return 0
    while lo < hi:  # pesquisa binária: maior n com fits(n)
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if fits(mid) else (lo, mid - 1)
    return lo


def payload_size(secret: Secret, encrypted: bool = False) -> int:
    return estimate_size(
        len(secret.content),
        filename=secret.filename,
        expires=secret.expires_at is not None,
        encrypted=encrypted,
    )


def make_payload(secret: Secret, password: str | None = None, now: float | None = None) -> bytes:
    """Segredo -> [metadados] -> [encriptação] -> cabeçalho + dados."""
    if secret.expires_at is not None and secret.expires_at <= (now or time.time()):
        raise InvalidSecretError("A data de validade tem de ser no futuro.")
    data = _plain_data(secret)
    if password:
        data = crypto.encrypt(data, password)
    if len(data) > MAX_DATA_BYTES:
        raise MessageTooLongError("O segredo excede o limite de 2 MB da aplicação.")
    return build_payload(data, encrypted=bool(password), meta=secret.needs_meta)


@dataclass(frozen=True)
class RevealResult:
    secret: Secret
    encrypted: bool
    data_bytes: int  # bytes de dados lidos (sem cabeçalho)

    @property
    def message(self) -> str:
        return self.secret.message

    @property
    def is_file(self) -> bool:
        return self.secret.is_file


def open_payload(
    header: Header, data: bytes, password: str | None = None, now: float | None = None
) -> RevealResult:
    """Faz o caminho inverso de ``make_payload`` sobre os dados extraídos."""
    verify_data(header, data)
    plain = data
    if header.encrypted:
        if not password:
            raise PasswordRequiredError(
                "Esta mensagem está encriptada. Introduza a palavra-passe."
            )
        plain = crypto.decrypt(data, password)

    kind, expires_at, name = KIND_TEXT, None, None
    if header.has_meta:
        kind, expires_at, name, plain = unpack_meta(plain)

    # A validade fica dentro da cifra (protegida pelo HMAC) quando há palavra-passe.
    if expires_at is not None and (now or time.time()) >= expires_at:
        raise ExpiredMessageError(
            f"Esta mensagem expirou em {format_datetime(expires_at)}. "
            "O StegoLab recusa revelá-la."
        )

    if kind == KIND_TEXT:
        try:
            plain.decode("utf-8")
        except UnicodeDecodeError:
            raise CorruptPayloadError(
                "Os dados extraídos não formam texto UTF-8 válido."
            ) from None
        secret = Secret(plain, None, expires_at)
    else:
        secret = Secret(plain, safe_filename(name or "ficheiro"), expires_at)
    return RevealResult(secret=secret, encrypted=header.encrypted, data_bytes=header.length)
