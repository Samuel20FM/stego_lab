"""Teste de fumo da interface: a aplicação arranca sem excepções."""

from __future__ import annotations

from conftest import ROOT
from streamlit.testing.v1 import AppTest


def test_app_starts_without_errors():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    labels = [t.label for t in at.tabs]
    assert any("Esconder mensagem" in label for label in labels)
    assert any("Extrair mensagem" in label for label in labels)


def test_bit_demo_reacts_to_input():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.text_input(key="demo_word").set_value("Moçambique").run()
    assert not at.exception
