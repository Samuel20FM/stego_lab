"""Núcleo de esteganografia LSB do StegoLab (independente da interface)."""

from .decoder import RevealResult, read_header, reveal_message
from .encoder import MAX_MESSAGE_BYTES, hide_message, required_bytes
from .errors import (
    CapacityError,
    CorruptPayloadError,
    EmptyMessageError,
    InvalidImageError,
    MessageTooLongError,
    NoPayloadError,
    PasswordRequiredError,
    StegoError,
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

__all__ = [
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
