import re

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
_PHONE_CHARS_RE = re.compile(r"^\+?[\d\s\-().]+$")


def parse_email(text: str) -> str | None:
    """Вернуть email или None, если формат явно неверный."""
    value = text.strip()
    if len(value) > 254 or ".." in value or not _EMAIL_RE.match(value):
        return None
    return value


def parse_phone(text: str) -> str | None:
    """Вернуть номер в аккуратном виде или None, если формат явно неверный.

    Допускаются пробелы, дефисы, скобки и ведущий «+»; цифр должно быть 10–15.
    Российские номера приводятся к виду +7XXXXXXXXXX.
    """
    value = text.strip()
    if len(value) > 30 or not _PHONE_CHARS_RE.match(value):
        return None
    digits = re.sub(r"\D", "", value)
    if not 10 <= len(digits) <= 15:
        return None
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10 and digits[0] == "9":
        return "+7" + digits
    return ("+" if value.startswith("+") else "") + digits
