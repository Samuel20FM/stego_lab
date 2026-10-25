"""Núcleo de esteganografia LSB do StegoLab (independente da interface)."""

from .decoder import RevealResult, read_header, reveal_message
from .encoder import MAX_MESSAGE_BYTES, hide_message, required_bytes
from .errors import (
    CapacityError,
    CorruptPayloadError,
    EmptyMessageError,
    ExpiredMessageError,
    InvalidFileError,
    InvalidImageError,
    InvalidSecretError,
    MessageTooLongError,
    NoPayloadError,
    PasswordRequiredError,
    StegoError,
    ToolMissingError,
    WrongPasswordError,
)
from .image_utils import (
    OUTPUT_FORMATS,
    ImageInfo,
    capacity_bytes,
    image_to_bytes,
    load_image,
    save_image,
)
from .secret import MAX_SECRET_FILE_BYTES, Secret, estimate_size, format_datetime, max_secret_file
from .carriers import COVER_TYPES, Carrier, Output, ffmpeg_available, hide, open_carrier, reveal

__all__ = [
    "COVER_TYPES",
    "Carrier",
    "ExpiredMessageError",
    "InvalidFileError",
    "InvalidSecretError",
    "MAX_SECRET_FILE_BYTES",
    "Output",
    "Secret",
    "ToolMissingError",
    "estimate_size",
    "max_secret_file",
    "ffmpeg_available",
    "format_datetime",
    "hide",
    "open_carrier",
    "reveal",
    "MAX_MESSAGE_BYTES",
    "OUTPUT_FORMATS",
    "CapacityError",
    "CorruptPayloadError",
    "EmptyMessageError",
    "ImageInfo",
    "InvalidImageError",
    "MessageTooLongError",
    "NoPayloadError",
    "PasswordRequiredError",
    "RevealResult",
    "StegoError",
    "WrongPasswordError",
    "capacity_bytes",
    "hide_message",
    "image_to_bytes",
    "load_image",
    "read_header",
    "required_bytes",
    "reveal_message",
    "save_image",
]
