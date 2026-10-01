import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import catalog, db
from bot.catalog import Service
from bot.keyboards import BTN_SHOWCASE, display_text, main_menu, normalize_button_text, service_card, SHOWCASE_ICON

router = Router()

SHOWCASE_INTRO = "Услуги студии «Персональный мастер». Выберите нужную и добавьте её в корзину."
SHOWCASE_EMPTY = (
    "Витрина временно недоступна. Пожалуйста, нажмите «Связаться с мастером», "
    "и Марина поможет с выбором."
)
NO_PRICE_TEXT = "уточняйте у мастера"
ADDED = "Добавлено в корзину: {name}"
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


@router.message(F.text.in_([BTN_SHOWCASE, display_text(BTN_SHOWCASE, SHOWCASE_ICON)]))
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
            reply_markup=service_card(service.id, has_price=service.has_price, in_cart=db.get_db().in_cart(user_id, service.id)),
        )


@router.callback_query(F.data == "showcase:open")
async def open_showcase(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await show_showcase(callback.message, state)


@router.callback_query(F.data.startswith(("cart:add:", "cart:in:")))
async def add_to_cart(callback: CallbackQuery) -> None:
    """«Добавить в корзину». Повторное нажатие (в том числе двойной тап) ничего не дублирует."""
    service_id = callback.data.rsplit(":", 1)[-1]
    service = catalog.CATALOG.get(service_id)
    if service is None or not service.has_price:
        await callback.answer(UNAVAILABLE, show_alert=True)
        return

    added = db.get_db().add_to_cart(callback.from_user.id, service_id)
    await callback.answer(ADDED.format(name=service.name) if added else ALREADY_IN_CART)
    if added:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=service_card(service_id, has_price=True, in_cart=True)
            )
        except TelegramBadRequest:
            logging.debug("Не удалось обновить кнопку под карточкой", exc_info=True)
