"""Portadores além da imagem, segredos em ficheiro e data de validade."""

from __future__ import annotations

import io
import time
import wave
import zipfile

import pytest

from conftest import make_image, to_bytes
from steganography import (
    CapacityError,
    ExpiredMessageError,
    InvalidFileError,
    InvalidSecretError,
    NoPayloadError,
    Secret,
    WrongPasswordError,
    ffmpeg_available,
    hide,
    open_carrier,
    reveal,
)
from steganography.carriers.text import ZW_CHARS
from steganography.payload import HEADER_SIZE


def make_wav(seconds: float = 1.0, channels: int = 2, width: int = 2, rate: int = 8000) -> bytes:
    import random

    rng = random.Random(4)
    frames = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(bytes(rng.randrange(256) for _ in range(frames * channels * width)))
    return buf.getvalue()


def make_pdf() -> bytes:
    return to_bytes(make_image(32, 32), "PDF")


def make_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


TEXT = "Relatório semanal da turma.\nNada de especial a assinalar.\n".encode("utf-8")

COVERS = {
    "png": lambda: to_bytes(make_image(64, 48)),
    "wav": make_wav,
    "txt": lambda: TEXT,
    "pdf": make_pdf,
    "docx": make_docx,
}


def _roundtrip(cover: bytes, secret: Secret, password=None, name="ficheiro"):
    out = hide(open_carrier(cover, name), secret, password)
    reopened = open_carrier(out.data, f"x.{out.ext}")
    return out, reveal(reopened, password)


@pytest.mark.parametrize("kind", sorted(COVERS))
def test_text_roundtrip_in_every_carrier(kind):
    secret = Secret.text("Encontro às 15h — ç ã 🔑")
    _, res = _roundtrip(COVERS[kind](), secret)
    assert res.message == "Encontro às 15h — ç ã 🔑"


@pytest.mark.parametrize("kind", sorted(COVERS))
def test_file_secret_with_password_in_every_carrier(kind):
    secret = Secret.file("relatório.pdf", bytes(range(256)) * 2)
    _, res = _roundtrip(COVERS[kind](), secret, password="UP-Maputo")
    assert res.is_file and res.secret.filename == "relatório.pdf"
    assert res.secret.content == secret.content
    assert res.encrypted


@pytest.mark.parametrize("kind", sorted(COVERS))
def test_carrier_without_payload(kind):
    with pytest.raises(NoPayloadError):
        reveal(open_carrier(COVERS[kind](), "x"))


def test_detection_is_by_content_not_extension():
    assert open_carrier(make_wav(), "musica.png").kind == "audio"
    assert open_carrier(to_bytes(make_image(), "PNG"), "nota.txt").kind == "image"
    assert open_carrier(make_docx(), "a.zip").ext == "docx"
    assert open_carrier(b"BMW e Toyota", "carros.txt").kind == "text"


@pytest.mark.parametrize(
    "data", [b"", b"\x00\x01\x02\x03" * 10, b"ID3\x03\x00" + b"\x00" * 30], ids=["vazio", "binario", "mp3"]
)
def test_unsupported_files_are_rejected(data):
    with pytest.raises(InvalidFileError):
        open_carrier(data, "x")


def test_wav_keeps_parameters_and_changes_only_lsb():
    cover = make_wav(width=2)
    out, _ = _roundtrip(cover, Secret.text("áudio"))
    with wave.open(io.BytesIO(cover)) as a, wave.open(io.BytesIO(out.data)) as b:
        assert a.getparams() == b.getparams()
        fa, fb = a.readframes(a.getnframes()), b.readframes(b.getnframes())
    assert fa[1::2] == fb[1::2]  # bytes altos intactos
    assert all(abs(x - y) <= 1 for x, y in zip(fa[0::2], fb[0::2]))


@pytest.mark.parametrize("width", [1, 3])
def test_wav_other_sample_widths(width):
    _, res = _roundtrip(make_wav(width=width), Secret.text(f"{width * 8} bits"))
    assert res.message == f"{width * 8} bits"


def test_wav_capacity_is_enforced():
    carrier = open_carrier(make_wav(seconds=0.05, channels=1), "x.wav")  # 400 amostras
    assert carrier.capacity() == 400 // 8 - HEADER_SIZE
    with pytest.raises(CapacityError):
        hide(carrier, Secret.text("x" * (carrier.capacity() + 1)))


def test_text_carrier_keeps_visible_text():
    out, _ = _roundtrip(TEXT, Secret.text("invisível"))
    stego = out.data.decode("utf-8")
    assert "".join(c for c in stego if c not in ZW_CHARS) == TEXT.decode("utf-8")
    assert any(c in ZW_CHARS for c in stego)


def test_text_carrier_replaces_previous_secret():
    first, _ = _roundtrip(TEXT, Secret.text("primeiro"))
    second, res = _roundtrip(first.data, Secret.text("segundo"))
    assert res.message == "segundo"
    assert len(second.data) < len(first.data) + 12 * 20


def test_text_with_emoji_zwj_sequences():
    cover = "Família 👨‍👩‍👧 reunida.".encode("utf-8")
    _, res = _roundtrip(cover, Secret.text("ok"))
    assert res.message == "ok"


def test_pdf_stays_structurally_identical():
    cover = make_pdf()
    out, _ = _roundtrip(cover, Secret.text("no PDF"))
    pos = cover.rfind(b"startxref")
    assert out.data.startswith(cover[:pos])  # nada antes de startxref muda
    assert out.data.endswith(cover[pos:])


def test_pdf_can_be_reused():
    first, _ = _roundtrip(make_pdf(), Secret.text("um"))
    _, res = _roundtrip(first.data, Secret.text("dois"))
    assert res.message == "dois"


def test_zip_members_are_untouched():
    cover = make_docx()
    out, _ = _roundtrip(cover, Secret.text("no Word"))
    with zipfile.ZipFile(io.BytesIO(cover)) as a, zipfile.ZipFile(io.BytesIO(out.data)) as b:
        assert a.namelist() == b.namelist()
        assert all(a.read(n) == b.read(n) for n in a.namelist())
        assert b.testzip() is None


def test_zip_comment_limit():
    carrier = open_carrier(make_docx(), "x.docx")
    with pytest.raises(CapacityError):
        hide(carrier, Secret.file("grande.bin", b"\x01" * 70_000))


# ---------------------------------------------------------------- validade


def test_secret_before_expiry_is_revealed():
    secret = Secret.text("ainda válido", expires_at=int(time.time()) + 3600)
    _, res = _roundtrip(COVERS["png"](), secret, password="pw")
    assert res.message == "ainda válido"
    assert res.secret.expires_at == secret.expires_at


@pytest.mark.parametrize("password", [None, "pw"])
def test_expired_secret_is_refused(password):
    expires = int(time.time()) + 60
    out = hide(open_carrier(COVERS["png"](), "x.png"), Secret.text("efémero", expires), password)
    with pytest.raises(ExpiredMessageError):
        reveal(open_carrier(out.data, "x.png"), password, now=expires + 1)


def test_expiry_in_the_past_is_rejected():
    with pytest.raises(InvalidSecretError):
        hide(open_carrier(COVERS["png"](), "x.png"), Secret.text("x", int(time.time()) - 10))


def test_expired_and_encrypted_still_needs_password_first():
    expires = int(time.time()) + 60
    out = hide(open_carrier(COVERS["png"](), "x.png"), Secret.text("x", expires), "certa")
    with pytest.raises(WrongPasswordError):
        reveal(open_carrier(out.data, "x.png"), "errada", now=expires + 1)


def test_output_must_fit_the_file_limit(monkeypatch):
    """Uma foto grande gera um PNG maior do que o original: tem de caber no limite."""
    import steganography.carriers as carriers

    carrier = open_carrier(COVERS["png"](), "x.png")
    out = hide(carrier, Secret.file("doc.pdf", b"%PDF" * 50), "certa")
    monkeypatch.setattr(carriers, "MAX_FILE_BYTES", len(out.data) - 1)
    with pytest.raises(CapacityError, match="ficheiro resultante"):
        hide(carrier, Secret.file("doc.pdf", b"%PDF" * 50), "certa")


def test_plain_text_keeps_original_format():
    """Sem ficheiro nem validade, o payload é igual ao da primeira versão."""
    carrier = open_carrier(COVERS["png"](), "x.png")
    header = open_carrier(hide(carrier, Secret.text("abc")).data, "x.png").read_header()
    assert header.length == 3 and not header.has_meta


def test_secret_filename_is_sanitised():
    assert Secret.file("../../etc/passwd", b"x").filename == "passwd"
    assert Secret.file("C:\\Users\\a\\nota.txt", b"x").filename == "nota.txt"


# ------------------------------------------------------------------ vídeo


@pytest.fixture(scope="module")
def mp4(tmp_path_factory) -> bytes:
    if not ffmpeg_available():
        pytest.skip("FFmpeg não instalado")
    import subprocess

    path = tmp_path_factory.mktemp("video") / "in.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x120:r=10:d=2",
         "-f", "lavfi", "-i", "sine=f=440:d=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )
    return path.read_bytes()


def test_video_roundtrip_keeps_video_stream(mp4):
    secret = Secret.file("plano.txt", "Reunião às 18h".encode())
    out, res = _roundtrip(mp4, secret, password="pw", name="clip.mp4")
    assert out.ext == "mkv" and res.secret == secret
    stego = open_carrier(out.data, "x.mkv")
    original = open_carrier(mp4, "clip.mp4")
    assert (stego.width, stego.height, stego.video_codec) == (original.width, original.height, original.video_codec)
    assert stego.audio_codec == "pcm_s16le"


def test_video_without_payload(mp4):
    with pytest.raises(NoPayloadError):
        reveal(open_carrier(mp4, "clip.mp4"))
