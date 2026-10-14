"""Encriptação opcional da mensagem (independente da lógica LSB).

* Derivação da chave: PBKDF2-HMAC-SHA256 com sal aleatório de 16 bytes.
* Cifra: Fernet (AES-128-CBC + HMAC-SHA256), da biblioteca ``cryptography``.

Formato produzido: ``sal (16 B) + token Fernet em binário``. O token é
guardado sem a codificação base64 para ocupar menos píxeis.

Nota: a esteganografia esconde a *existência* da mensagem; a encriptação
protege o *conteúdo* caso a mensagem seja descoberta.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .errors import CorruptPayloadError, WrongPasswordError

SALT_SIZE = 16
KDF_ITERATIONS = 480_000
# Token Fernet binário: versão (1) + timestamp (8) + IV (16) + HMAC (32)
_FERNET_FIXED_OVERHEAD = 1 + 8 + 16 + 32
_AES_BLOCK = 16


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=KDF_ITERATIONS
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt(data: bytes, password: str) -> bytes:
    salt = os.urandom(SALT_SIZE)
    token = Fernet(_derive_key(password, salt)).encrypt(data)
    return salt + base64.urlsafe_b64decode(token)


def decrypt(blob: bytes, password: str) -> bytes:
    if len(blob) < SALT_SIZE + _FERNET_FIXED_OVERHEAD + _AES_BLOCK:
        raise CorruptPayloadError("Os dados encriptados estão incompletos.")
    salt, raw_token = blob[:SALT_SIZE], blob[SALT_SIZE:]
    token = base64.urlsafe_b64encode(raw_token)
    try:
        return Fernet(_derive_key(password, salt)).decrypt(token)
    except InvalidToken:
        raise WrongPasswordError(
            "Palavra-passe incorrecta: não foi possível desencriptar a mensagem."
        ) from None


def encrypted_size(plain_size: int) -> int:
    """Número exacto de bytes produzidos por ``encrypt`` para ``plain_size`` bytes."""
    padded = (plain_size // _AES_BLOCK + 1) * _AES_BLOCK  # padding PKCS7
    return SALT_SIZE + _FERNET_FIXED_OVERHEAD + padded
