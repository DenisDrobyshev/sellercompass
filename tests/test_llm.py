"""Tests for the optional LLM explanation layer — no network, no API key."""

from core.engine.decide import decide
from core.llm import explain_decision
from core.models.product import Product


def _p(reviews, rating, *, brand="B", name="термокружка стальная", price=1000):
    return Product(
        marketplace="wildberries", external_id=1, name=name,
        reviews=reviews, rating=rating, price=price, brand=brand,
    )


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessages:
    def __init__(self, text, raises):
        self._text = text
        self._raises = raises

    def create(self, **_kwargs):
        if self._raises:
            raise RuntimeError("api down")
        return type("Msg", (), {"content": [_FakeBlock(self._text)]})


class _FakeClient:
    def __init__(self, text="fine", raises=False):
        self.messages = _FakeMessages(text, raises)


def _go():
    return decide("q", [_p(500, 4.2, brand=f"B{i}") for i in range(12)], budget=100000)


def _kill():
    return decide("q", [_p(5, 4.2, brand=f"B{i}") for i in range(3)], budget=100000)


def test_template_used_without_key():
    text = explain_decision(_go())  # default settings carry no key
    assert "worth starting" in text


def test_template_kill_wording():
    assert "not worth pursuing" in explain_decision(_kill())


def test_llm_path_uses_injected_client():
    text = explain_decision(_go(), client=_FakeClient("Because demand is strong."))
    assert text == "Because demand is strong."


def test_llm_error_falls_back_to_template():
    text = explain_decision(_kill(), client=_FakeClient(raises=True))
    assert "not worth pursuing" in text
