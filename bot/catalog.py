"""Каталог услуг для витрины. Источник — таблица услуг в knowledge/personal_master.md."""
import hashlib
import logging
import re
from dataclasses import dataclass

from bot.config import BASE_DIR

KNOWLEDGE_PATH = BASE_DIR / "knowledge" / "personal_master.md"


@dataclass(frozen=True)
class Service:
    id: str            # короткий устойчивый идентификатор (хеш названия) для кнопок
    name: str
    description: str
    price: str         # цена как в базе знаний, например «1 800 ₽» или «300 ₽ за два ногтя»

    @property
    def has_price(self) -> bool:
        """Цена есть, если в ячейке встречается хотя бы одна цифра («—», пусто, «договорная» — нет)."""
        return bool(re.search(r"\d", self.price))

    @property
    def amount(self) -> int | None:
        """Точная цена в рублях. None, если цена не фиксированная: варианты («3 000 ₽ или 5 000 ₽»),
        единица измерения («300 ₽ за два ногтя»), «от …» и т. п. Такие позиции не входят в итог."""
        match = re.fullmatch(r"(\d[\d\s\u00a0\u202f]*)\s*(?:₽|руб\.?|р\.?)", self.price.strip(), re.IGNORECASE)
        if not match:
            return None
        return int(re.sub(r"\D", "", match.group(1)))


def format_price(amount: int) -> str:
    """1800 -> «1 800 ₽»."""
    return f"{amount:,}".replace(",", " ") + " ₽"


class Catalog:
    def __init__(self, services: list[Service]):
        self.services = services
        self._by_id = {s.id: s for s in services}

    def get(self, service_id: str) -> Service | None:
        return self._by_id.get(service_id)


def _service_id(name: str) -> str:
    return hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:8]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells)


def _parse_table(rows: list[list[str]]) -> list[Service] | None:
    header = [c.lower() for c in rows[0]]

    def col(word: str) -> int | None:
        return next((i for i, c in enumerate(header) if word in c), None)

    name_i, price_i, desc_i = col("услуг"), col("цен"), col("описан")
    if name_i is None or price_i is None:
        return None  # это другая таблица, не список услуг

    services, seen = [], set()
    for cells in rows[1:]:
        if _is_separator(cells):
            continue
        name = cells[name_i] if name_i < len(cells) else ""
        if not name:
            continue
        service = Service(
            id=_service_id(name),
            name=name,
            description=cells[desc_i] if desc_i is not None and desc_i < len(cells) else "",
            price=cells[price_i] if price_i < len(cells) else "",
        )
        if service.id in seen:
            logging.warning("Дубль услуги в базе знаний пропущен: %s", name)
            continue
        seen.add(service.id)
        services.append(service)
    return services


def parse_services(markdown: str) -> list[Service]:
    """Найти в markdown таблицу с колонками «Услуга» и «Цена» и разобрать её."""
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        block = []
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            block.append(_cells(lines[i]))
            i += 1
        parsed = _parse_table(block)
        if parsed is not None:
            return parsed
    return []


def load_catalog() -> Catalog:
    return Catalog(parse_services(KNOWLEDGE_PATH.read_text(encoding="utf-8")))


CATALOG = load_catalog()
