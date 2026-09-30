from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_SHOWCASE = "Витрина"
BTN_CART = "Корзина"
BTN_CONTACT = "Связаться с человеком"

BTN_ADD_TO_CART = "Добавить в корзину"
BTN_IN_CART = "✓ В корзине"
BTN_ASK_PRICE = "Уточнить стоимость"


def main_menu() -> ReplyKeyboardMarkup:
    """Постоянное меню под полем ввода."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SHOWCASE), KeyboardButton(text=BTN_CART)],
            [KeyboardButton(text=BTN_CONTACT)],
        ],
        resize_keyboard=True,
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
