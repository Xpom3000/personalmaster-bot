from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_SHOWCASE = "Витрина"
BTN_CART = "Корзина"
BTN_CONTACT = "Связаться с мастером"
LEGACY_BTN_CONTACT = "Связаться с человеком"

SHOWCASE_ICON = "🛍"
CART_ICON = "🧺"
CONTACT_ICON = "💬"

BTN_ADD_TO_CART = "Добавить в корзину"
BTN_IN_CART = "✓ В корзине"
BTN_ASK_PRICE = "Уточнить стоимость"
BTN_OPEN_CATALOG = "Открыть витрину"
BTN_CHECKOUT = "Оформить заказ"
BTN_PAY = "Оплатить"
BTN_PAY_NOW = "Оплатить заказ"
BTN_PAID = "Я оплатил"


def display_text(label: str, icon: str) -> str:
    return f"{icon} {label}"


def normalize_button_text(text: str) -> str:
    for icon in (SHOWCASE_ICON, CART_ICON, CONTACT_ICON):
        text = text.replace(f"{icon} ", "")
    return text.strip()


def main_menu() -> ReplyKeyboardMarkup:
    """Постоянное меню под полем ввода.

    Telegram не умеет задавать настоящие разные цвета стандартным ReplyKeyboardMarkup,
    поэтому делаем визуальную дифференциацию иконками и пространством кнопок.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=display_text(BTN_SHOWCASE, SHOWCASE_ICON)), KeyboardButton(text=display_text(BTN_CART, CART_ICON))],
            [KeyboardButton(text=display_text(BTN_CONTACT, CONTACT_ICON))],
        ],
        resize_keyboard=True,
        row_width=2,
        is_persistent=True,
    )


def method_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Telegram", callback_data="lead:telegram"),
                InlineKeyboardButton(text="Email", callback_data="lead:email"),
                InlineKeyboardButton(text="Телефон", callback_data="lead:phone"),
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="lead:cancel")],
        ]
    )


def cancel_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="lead:cancel")]]
    )


def service_card(service_id: str, *, has_price: bool, in_cart: bool) -> InlineKeyboardMarkup:
    """Кнопка под карточкой услуги.

    Есть цена: «Добавить в корзину» (после добавления — «✓ В корзине»).
    Цены в базе нет: «Уточнить стоимость» — запускает заявку на связь.
    """
    if not has_price:
        button = InlineKeyboardButton(text=BTN_ASK_PRICE, callback_data=f"ask:{service_id}")
    elif in_cart:
        button = InlineKeyboardButton(text=BTN_IN_CART, callback_data=f"cart:in:{service_id}")
    else:
        button = InlineKeyboardButton(text=BTN_ADD_TO_CART, callback_data=f"cart:add:{service_id}")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def _short(name: str, limit: int = 24) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def cart_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """items — пары (service_id, название) в порядке списка. У каждой позиции своя «Убрать»."""
    rows = [
        [InlineKeyboardButton(text=f"Убрать {i}. {_short(name)}", callback_data=f"cart:rm:{sid}")]
        for i, (sid, name) in enumerate(items, start=1)
    ]
    rows.append([InlineKeyboardButton(text=BTN_CHECKOUT, callback_data="order:create")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def order_payment_keyboard(order_id: int, *, payment_url: str | None = None) -> InlineKeyboardMarkup:
    """Кнопки для оплаты заказа: либо создать платёж, либо показать ссылку и кнопку подтверждения."""
    if payment_url:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=BTN_PAY_NOW, url=payment_url)],
                [InlineKeyboardButton(text=BTN_PAID, callback_data=f"order:paid:{order_id}")],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_PAY, callback_data=f"order:pay:{order_id}")]]
    )


def anons_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_OPEN_CATALOG, callback_data="showcase:open")]]
    )
