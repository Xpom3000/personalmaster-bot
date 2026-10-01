import html
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import catalog, db
from bot.catalog import Service, format_price
from bot.db import Order, OrderLine
from bot.keyboards import BTN_CART, CART_ICON, cart_keyboard, display_text, main_menu, normalize_button_text, order_payment_keyboard
from bot.services.notify import notify_owner
from bot.services import yookassa

router = Router()

CART_TITLE = "<b>Ваша корзина</b>"
EMPTY_CART = "Ваша корзина пуста. Откройте «Витрину», чтобы выбрать услуги."
REMOVED = "Услуга убрана из корзины"
ALREADY_REMOVED = "Эта услуга уже убрана из корзины"
CART_EMPTY_ALERT = "Корзина пуста. Возможно, заказ уже оформлен. Откройте «Витрину», чтобы выбрать услуги."
DROPPED_NOTE = "Некоторые услуги больше недоступны и убраны из корзины."
VARIABLE_NOTE = (
    "* Стоимость отмеченных позиций зависит от выбора или объёма и в итог не входит: "
    "точную сумму уточнит мастер."
)
ORDER_TITLE = "<b>Заказ № {id} оформлен</b>"
ORDER_STATUS = "Статус: {status}"
ORDER_PAYMENT_NOTE = (
    "Чтобы завершить заказ, нажмите кнопку «Оплатить», завершите оплату и затем нажмите «Я оплатил»."
)
ORDER_FAILED = "К сожалению, не удалось оформить заказ. Пожалуйста, попробуйте ещё раз чуть позже."
PAYMENT_FAILED = "Не удалось создать оплату. Пожалуйста, попробуйте ещё раз чуть позже."
PAYMENT_CHECK_FAILED = "Оплата ещё не завершена. Пожалуйста, завершите оплату по ссылке."
PAYMENT_LINK_TEXT = "<b>Оплата заказа № {id}</b>\n\nПерейдите по ссылке ниже и оплатите заказ на сумму <b>{total}</b>.\n\n<a href=\"{url}\">Оплатить заказ</a>\n\nПосле оплаты нажмите кнопку «Я оплатил»."
PAYMENT_PAID_TEXT = "<b>Спасибо! Оплата подтверждена.</b>\n\nВаш заказ № {id} оплачен и уже в работе."
PAYMENT_ADMIN_TEXT = "<b>Новый оплаченный заказ</b>\n\nЗаказ № {id}\nСумма: {total} ₽\nКлиент: {name}\nUsername: {username}\nTelegram ID: <code>{user_id}</code>"


def _line(index: int, name: str, price_text: str, amount: int | None) -> str:
    mark = " *" if amount is None else ""
    return f"{index}. {html.escape(name)} — {html.escape(price_text)}{mark}"


def _total_line(total: int, has_variable: bool) -> str:
    if total == 0 and has_variable:
        return "<b>Итого: сумму определит мастер</b>"
    suffix = " (без учёта позиций, отмеченных *)" if has_variable else ""
    return f"<b>Итого: {format_price(total)}</b>{suffix}"


def _lines_and_total(lines: list[tuple[str, str, int | None]]) -> str:
    """Текст со списком позиций и итогом. lines — (название, цена как в базе, сумма или None)."""
    body = "\n".join(_line(i, n, p, a) for i, (n, p, a) in enumerate(lines, start=1))
    total = sum(a for _, _, a in lines if a is not None)
    has_variable = any(a is None for _, _, a in lines)
    text = f"{body}\n\n{_total_line(total, has_variable)}"
    if has_variable:
        text += f"\n\n{VARIABLE_NOTE}"
    return text


def build_cart_view(user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    """Текст и кнопки корзины по данным из базы. Если корзина пуста, кнопок нет."""
    database = db.get_db()
    services: list[Service] = []
    dropped = 0
    for sid in database.cart_service_ids(user_id):
        service = catalog.CATALOG.get(sid)
        if service and service.has_price:
            services.append(service)
        else:  # услуга исчезла из базы знаний или потеряла цену
            database.remove_from_cart(user_id, sid)
            dropped += 1

    note = f"\n\n{DROPPED_NOTE}" if dropped else ""
    if not services:
        return EMPTY_CART + note, None

    text = f"{CART_TITLE}\n\n" + _lines_and_total([(s.name, s.price, s.amount) for s in services]) + note
    return text, cart_keyboard([(s.id, s.name) for s in services])


def build_order_text(order: Order) -> str:
    lines = [(l.name, l.price_text, l.amount) for l in order.lines]
    return (
        f"{ORDER_TITLE.format(id=order.id)}\n"
        f"{ORDER_STATUS.format(status=order.status)}\n\n"
        f"{_lines_and_total(lines)}\n\n"
        f"{ORDER_PAYMENT_NOTE}"
    )


def build_payment_text(order: Order) -> str:
    if not order.payment_url:
        raise ValueError("У заказа нет ссылки на оплату")
    return PAYMENT_LINK_TEXT.format(id=order.id, total=format_price(order.total), url=order.payment_url)


def build_paid_text(order: Order) -> str:
    return PAYMENT_PAID_TEXT.format(id=order.id)


def build_order_markup(order: Order) -> InlineKeyboardMarkup | None:
    if order.status == db.STATUS_PAID:
        return None
    return order_payment_keyboard(order.id, payment_url=order.payment_url)


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    """Обновить сообщение с корзиной; «сообщение не изменилось» (двойное нажатие) не ошибка."""
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    except TelegramBadRequest:
        logging.debug("Сообщение с корзиной не обновлено", exc_info=True)


@router.message(F.text.in_([BTN_CART, display_text(BTN_CART, CART_ICON)]))
async def show_cart(message: Message, state: FSMContext) -> None:
    await state.clear()  # меню доступно всегда: незавершённая заявка сбрасывается
    if message.text:
        message.text = normalize_button_text(message.text)
    text, markup = build_cart_view(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=markup or main_menu())


@router.callback_query(F.data.startswith("cart:rm:"))
async def remove_item(callback: CallbackQuery) -> None:
    """«Убрать». Двойное нажатие безопасно: корзина просто перерисовывается по текущему состоянию базы."""
    service_id = callback.data.rsplit(":", 1)[-1]
    removed = db.get_db().remove_from_cart(callback.from_user.id, service_id)
    await callback.answer(REMOVED if removed else ALREADY_REMOVED)
    text, markup = build_cart_view(callback.from_user.id)
    await _edit(callback, text, markup)


@router.callback_query(F.data == "order:create")
async def create_order(callback: CallbackQuery) -> None:
    """«Оформить заказ»: заказ «ожидает оплаты» создаётся, корзина очищается — одной транзакцией."""
    user = callback.from_user
    try:
        order = db.get_db().create_order_from_cart(
            user.id, user.username, user.full_name, catalog.CATALOG.get
        )
    except Exception:
        logging.exception("Не удалось создать заказ")
        await callback.answer(ORDER_FAILED, show_alert=True)
        return

    if order is None:  # пустая корзина или повторное нажатие после оформления
        await callback.answer(CART_EMPTY_ALERT, show_alert=True)
        await _edit(callback, EMPTY_CART, None)
        return

    await callback.answer()
    await _edit(callback, build_order_text(order), build_order_markup(order))


@router.callback_query(F.data.startswith("order:pay:"))
async def create_payment(callback: CallbackQuery) -> None:
    """Создать платёж в ЮKassa и показать ссылку на оплату."""
    try:
        order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("Некорректный заказ.", show_alert=True)
        return

    order = db.get_db().get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден.", show_alert=True)
        return
    if order.status == db.STATUS_PAID:
        await callback.answer("Заказ уже оплачен.", show_alert=True)
        return
    if order.payment_id and order.payment_url:
        await callback.answer("Ссылка на оплату уже создана.", show_alert=True)
        await _edit(callback, build_payment_text(order), build_order_markup(order))
        return

    try:
        payment_id, payment_url = await yookassa.create_payment_for_order(order)
    except Exception:
        logging.exception("Не удалось создать платёж ЮKassa")
        await callback.answer(PAYMENT_FAILED, show_alert=True)
        return

    db.get_db().set_order_payment(order_id, payment_id, payment_url)
    order = db.get_db().get_order(order_id)
    await callback.answer()
    await _edit(callback, build_payment_text(order), build_order_markup(order))


@router.callback_query(F.data.startswith("order:paid:"))
async def check_payment(callback: CallbackQuery) -> None:
    """Проверить статус оплаты в ЮKassa."""
    try:
        order_id = int(callback.data.rsplit(":", 1)[-1])
    except ValueError:
        await callback.answer("Некорректный заказ.", show_alert=True)
        return

    order = db.get_db().get_order(order_id)
    if order is None:
        await callback.answer("Заказ не найден.", show_alert=True)
        return
    if order.status == db.STATUS_PAID:
        await callback.answer("Заказ уже оплачен.", show_alert=True)
        return
    if not order.payment_id:
        await callback.answer("Сначала откройте ссылку на оплату и завершите платёж.", show_alert=True)
        return

    try:
        status = await yookassa.check_payment_status(order.payment_id)
    except Exception:
        logging.exception("Не удалось проверить статус оплаты в ЮKassa")
        await callback.answer(PAYMENT_CHECK_FAILED, show_alert=True)
        return

    if status == "succeeded":
        db.get_db().mark_order_paid(order_id)
        order = db.get_db().get_order(order_id)
        await callback.answer("Спасибо! Оплата подтверждена.", show_alert=True)
        await _edit(callback, build_paid_text(order), None)
        admin_text = PAYMENT_ADMIN_TEXT.format(
            id=order.id,
            total=order.total,
            name=html.escape(callback.from_user.full_name or callback.from_user.first_name or "Клиент"),
            username=html.escape(callback.from_user.username or "-"),
            user_id=callback.from_user.id,
        )
        await notify_owner(callback.bot, admin_text)
        return

    await callback.answer(PAYMENT_CHECK_FAILED, show_alert=True)
    await _edit(callback, build_payment_text(order), build_order_markup(order))
