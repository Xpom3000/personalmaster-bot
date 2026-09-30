import pytest

from bot.validators import parse_email, parse_phone


@pytest.mark.parametrize("text", ["name@example.com", " anna.k+nails@mail.ru ", "a@b.co", "user_1@sub.domain.org"])
def test_valid_email(text):
    assert parse_email(text) == text.strip()


@pytest.mark.parametrize("text", ["", "hello", "name@", "@example.com", "name@example", "na me@example.com",
                                  "name@@example.com", "name@exa..mple.com", "name@example.c", "a" * 250 + "@x.com"])
def test_invalid_email(text):
    assert parse_email(text) is None


@pytest.mark.parametrize("text,expected", [
    ("+7 900 123-45-67", "+79001234567"),
    ("8 (900) 123-45-67", "+79001234567"),
    ("89001234567", "+79001234567"),
    ("9001234567", "+79001234567"),
    ("+44 20 7946 0958", "+442079460958"),
])
def test_valid_phone(text, expected):
    assert parse_phone(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "12345", "телефон 89001234567", "+7 900 123-45-6a",
                                  "1234567890123456", "12+3456789012", "89001234567 89001234567"])
def test_invalid_phone(text):
    assert parse_phone(text) is None
