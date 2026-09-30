import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import cart, catalog
from bot.catalog import Service
from bot.keyboards import BTN_CART, BTN_SHOWCASE, main_menu, service_card

router = Router()

SHOWCASE_INTRO = "Услуги студии «Персональный мастер». Выберите нужную и добавьте её в корзину."
SHOWCASE_EMPTY = (
    "Витрина временно недоступна. Пожалуйста, нажмите «Связаться с человеком», "
    "и Марина поможет с выбором."
)
NO_PRICE_TEXT = "уточняйте у мастера"
CART_STUB = "Раздел «Корзина» находится в разработке: оформление заказа и оплата появятся в ближайшее время."
CART_SAVED = "Выбранные вами услуги сохранены:"
ADDED = "Услуга добавлена в корзину"
ALREADY_IN_CART = "Эта услуга уже в корзине"
UNAVAILABLE = "Эта услуга больше недоступна. Пожалуйста, откройте витрину ещё раз."


def card_text(service: Service) -> str:
    """Карточка услуги (HTML): название, описание, цена."""
    lines = [f"<b>{html.escape(service.name)}</b>"]
    if service.description:
        lines.append(html.escape(service.description))
    price = html.escape(service.price) if service.has_price else NO_PRICE_TEXT
    lines.append(f"Цена: {price}")
    return "\n".join(lines)


@router.message(F.text == BTN_SHOWCASE)
async def show_showcase(message: Message, state: FSMContext) -> None:
    await state.clear()  # меню доступно всегда: незавершённая заявка сбрасывается
    services = catalog.CATALOG.services
    if not services:
        await message.answer(SHOWCASE_EMPTY, reply_markup=main_menu())
        return
    user_id = message.from_user.id
    await message.answer(SHOWCASE_INTRO, reply_markup=main_menu())
    for service in services:
        await message.answer(
            card_text(service),
            parse_mode="HTML",
            reply_markup=service_card(service.id, has_price=service.has_price, in_cart=cart.contains(user_id, service.id)),
        )


@router.message(F.text == BTN_CART)
async def show_cart(message: Message, state: FSMContext) -> None:
    """Заглушка: полноценная корзина будет на следующем этапе."""
    await state.clear()
    lines = [CART_STUB]
    names = [s.name for sid in cart.items(message.from_user.id) if (s := catalog.CATALOG.get(sid))]
    if names:
        lines.append(f"\n{CART_SAVED}\n" + "\n".join(f"- {n}" for n in names))
    await message.answer("\n".join(lines), reply_markup=main_menu())


@router.callback_query(F.data.startswith("cart:"))
async def add_to_cart(callback: CallbackQuery) -> None:
    """«Добавить в корзину». Повторное нажатие (в том числе двойной тап) ничего не дублирует."""
    service_id = callback.data.rsplit(":", 1)[-1]
    service = catalog.CATALOG.get(service_id)
    if service is None or not service.has_price:
        await callback.answer(UNAVAILABLE, show_alert=True)
        return

    added = cart.add(callback.from_user.id, service_id)
    await callback.answer(ADDED if added else ALREADY_IN_CART)
    if added:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=service_card(service_id, has_price=True, in_cart=True)
            )
        except TelegramBadRequest:
            logging.debug("Не удалось обновить кнопку под карточкой", exc_info=True)
