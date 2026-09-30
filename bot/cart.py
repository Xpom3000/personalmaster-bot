"""Корзина в памяти процесса. При перезапуске бота очищается (хранилище появится на этапе заказа)."""
from collections import defaultdict

# user_id -> {service_id: None}; словарь хранит порядок добавления
_carts: dict[int, dict[str, None]] = defaultdict(dict)


def add(user_id: int, service_id: str) -> bool:
    """Добавить услугу. False, если она уже была в корзине (повторное нажатие)."""
    cart = _carts[user_id]
    if service_id in cart:
        return False
    cart[service_id] = None
    return True


def contains(user_id: int, service_id: str) -> bool:
    return service_id in _carts.get(user_id, {})


def items(user_id: int) -> list[str]:
    return list(_carts.get(user_id, {}))


def clear_all() -> None:
    _carts.clear()
