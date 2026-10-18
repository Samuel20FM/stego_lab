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


def test_secret_kind_and_validity_controls():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.button_group(key="hide_kind_0").set_value("Ficheiro").run()
    assert not at.exception
    at.button_group(key="hide_validity_0").set_value("Personalizada").run()
    assert not at.exception
    assert at.date_input(key="hide_date_0") is not None
