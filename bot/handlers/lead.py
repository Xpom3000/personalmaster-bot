import logging
import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User

from bot import catalog, guardrails
from bot.keyboards import BTN_CONTACT, cancel_only, main_menu, method_choice
from bot.services.notify import build_lead_message, notify_owner
from bot.validators import parse_email, parse_phone

router = Router()

ASK_METHOD = "Как вам удобнее связаться? Выберите способ, и я передам вашу заявку мастеру."
ASK_EMAIL = "Введите, пожалуйста, ваш email."
ASK_PHONE = "Введите, пожалуйста, номер телефона, например: +7 900 123-45-67."
BAD_EMAIL = (
    "Не удалось распознать email. Проверьте, пожалуйста, адрес и отправьте его ещё раз, "
    "например: name@example.com. Чтобы отменить заявку, напишите «отмена»."
)
BAD_PHONE = (
    "Не удалось распознать номер телефона. Отправьте, пожалуйста, номер ещё раз, "
    "например: +7 900 123-45-67. Чтобы отменить заявку, напишите «отмена»."
)
CHOOSE_BUTTONS = "Пожалуйста, выберите способ связи кнопками ниже или напишите «отмена»."
NEED_TEXT = "Пожалуйста, отправьте ответ текстом или напишите «отмена»."
CANCELLED = "Хорошо, заявка отменена. Если понадобится, нажмите «Связаться с человеком»."
DONE = "Спасибо, заявка принята. Марина скоро свяжется с вами."
FAILED = "К сожалению, не удалось передать заявку. Пожалуйста, попробуйте чуть позже."
ALREADY = "Ваши заявки уже приняты. Марина скоро свяжется с вами, пожалуйста, подождите."
STALE = "Эта кнопка уже неактуальна. Нажмите «Связаться с человеком», чтобы оставить заявку."

CANCEL_WORDS = {"отмена", "отменить", "передумал", "передумала", "не надо", "не хочу", "стоп"}

# Защита от спама заявками: не больше 5 в час от одного пользователя
_lead_limiter = guardrails.RateLimiter(limit=5, window=3600)


class LeadForm(StatesGroup):
    method = State()
    email = State()
    phone = State()


def _is_cancel(text: str | None) -> bool:
    if not text:
        return False
    return re.sub(r"[^\w\s]", "", text.lower().replace("ё", "е")).strip() in CANCEL_WORDS


async def _submit(bot: Bot, user: User, method: str, contact: str | None, state: FSMContext) -> None:
    """Отправить заявку владельцу и ответить клиенту."""
    topic = (await state.get_data()).get("topic")
    await state.clear()
    if not _lead_limiter.allow(user.id):
        await bot.send_message(user.id, ALREADY, reply_markup=main_menu())
        return
    try:
        await notify_owner(bot, build_lead_message(user, method, contact, topic))
    except Exception:
        logging.exception("Не удалось отправить заявку владельцу (проверьте ADMIN_ID и что владелец нажал /start)")
        await bot.send_message(user.id, FAILED, reply_markup=main_menu())
        return
    await bot.send_message(user.id, DONE, reply_markup=main_menu())


# --- начало сценария: кнопка «Связаться с человеком» (работает в любом состоянии) ---
@router.message(F.text == BTN_CONTACT)
async def start_lead(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(LeadForm.method)
    await message.answer(ASK_METHOD, reply_markup=method_choice())


# --- «Уточнить стоимость» под карточкой услуги без цены ---
@router.callback_query(F.data.startswith("ask:"))
async def ask_price(callback: CallbackQuery, state: FSMContext) -> None:
    service = catalog.CATALOG.get(callback.data.split(":", 1)[1])
    await callback.answer()
    await state.clear()
    await state.set_state(LeadForm.method)
    if service:
        await state.update_data(topic=f"уточнить стоимость услуги «{service.name}»")
    await callback.bot.send_message(callback.from_user.id, ASK_METHOD, reply_markup=method_choice())


# --- отмена ---
@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELLED, reply_markup=main_menu())


@router.message(StateFilter(LeadForm), F.text.func(_is_cancel))
async def cancel_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELLED, reply_markup=main_menu())


@router.callback_query(StateFilter(LeadForm), F.data == "lead:cancel")
async def cancel_button(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.bot.send_message(callback.from_user.id, CANCELLED, reply_markup=main_menu())


# --- выбор способа связи ---
@router.callback_query(StateFilter(LeadForm.method), F.data == "lead:telegram")
async def choose_telegram(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _submit(callback.bot, callback.from_user, "telegram", None, state)


@router.callback_query(StateFilter(LeadForm.method), F.data == "lead:email")
async def choose_email(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(LeadForm.email)
    await callback.bot.send_message(callback.from_user.id, ASK_EMAIL, reply_markup=cancel_only())


@router.callback_query(StateFilter(LeadForm.method), F.data == "lead:phone")
async def choose_phone(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(LeadForm.phone)
    await callback.bot.send_message(callback.from_user.id, ASK_PHONE, reply_markup=cancel_only())


@router.callback_query(F.data.startswith("lead:"))
async def stale_button(callback: CallbackQuery) -> None:
    """Кнопка из старого сообщения, когда сценарий уже завершён или другой шаг."""
    await callback.answer(STALE, show_alert=True)


# --- ввод данных ---
@router.message(StateFilter(LeadForm.method), F.text)
async def method_wrong_input(message: Message) -> None:
    await message.answer(CHOOSE_BUTTONS, reply_markup=method_choice())


@router.message(StateFilter(LeadForm.email), F.text)
async def got_email(message: Message, state: FSMContext) -> None:
    email = parse_email(message.text)
    if email is None:
        await message.answer(BAD_EMAIL, reply_markup=cancel_only())
        return
    await _submit(message.bot, message.from_user, "email", email, state)


@router.message(StateFilter(LeadForm.phone), F.text)
async def got_phone(message: Message, state: FSMContext) -> None:
    phone = parse_phone(message.text)
    if phone is None:
        await message.answer(BAD_PHONE, reply_markup=cancel_only())
        return
    await _submit(message.bot, message.from_user, "phone", phone, state)


@router.message(StateFilter(LeadForm))
async def non_text_input(message: Message) -> None:
    """Стикер, фото и т. п. посреди сценария."""
    await message.answer(NEED_TEXT)
