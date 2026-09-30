from bot import catalog
from bot.catalog import parse_services

SAMPLE = """
# Заголовок

Не таблица.

| Другая таблица | Значение |
|---|---|
| a | b |

| Цена | Услуга | Описание |
|:--|:--|---|
| 500 ₽ | Стрижка | Быстро и аккуратно |
|  | Консультация | Подберём форму |
| — | Сертификат | На любую услугу |
| договорная | Особый уход | Индивидуально |
|  |  | строка без названия |
| 700 ₽ | Стрижка | дубль |
| 900 ₽ | Окрашивание |
"""


def test_real_knowledge_base_has_services():
    names = [s.name for s in catalog.CATALOG.services]
    assert len(names) == 7
    assert "Маникюр с покрытием гель-лаком" in names and "Подарочный сертификат" in names
    gel = catalog.CATALOG.services[0]
    assert gel.price == "1 800 ₽" and gel.description.startswith("Уход за ногтями") and gel.has_price
    assert all(s.has_price for s in catalog.CATALOG.services)


def test_ids_unique_and_lookup():
    ids = [s.id for s in catalog.CATALOG.services]
    assert len(ids) == len(set(ids))
    assert catalog.CATALOG.get(ids[0]) is catalog.CATALOG.services[0]
    assert catalog.CATALOG.get("нет-такого") is None


def test_parse_sample_columns_in_any_order():
    services = {s.name: s for s in parse_services(SAMPLE)}
    assert list(services) == ["Стрижка", "Консультация", "Сертификат", "Особый уход", "Окрашивание"]
    assert services["Стрижка"].price == "500 ₽" and services["Стрижка"].description == "Быстро и аккуратно"


def test_missing_price_detected():
    services = {s.name: s for s in parse_services(SAMPLE)}
    assert services["Стрижка"].has_price
    for name in ["Консультация", "Сертификат", "Особый уход"]:
        assert not services[name].has_price, name
    # короткая строка без части ячеек не ломает разбор
    assert services["Окрашивание"].has_price and services["Окрашивание"].description == ""


def test_row_without_price_cell():
    md = "| Услуга | Описание | Цена |\n|---|---|---|\n| Особый уход | Индивидуально |\n| Массаж |\n"
    services = parse_services(md)
    assert [s.name for s in services] == ["Особый уход", "Массаж"]
    assert not services[0].has_price and services[1].description == "" and not services[1].has_price


def test_no_table_gives_empty_catalog():
    assert parse_services("просто текст\n\n| a | b |\n|---|---|\n| 1 | 2 |") == []
