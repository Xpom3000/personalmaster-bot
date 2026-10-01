# Бот бьюти-студии «Персональный мастер»

Telegram-бот: консультирует по услугам через ИИ, собирает заявки и принимает оплату. Подробности — в `CLAUDE.md`.

## Подготовка DeepSeek

Укажите ключ DeepSeek в `.env`:

```env
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

## Заявки владельцу

Укажите в `.env` `ADMIN_ID` — числовой Telegram ID владельца (его покажет бот @userinfobot). Владелец должен один раз нажать `/start` в этом боте, иначе Telegram не даст боту написать ему.

## Запуск локально

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # вставить BOT_TOKEN и ADMIN_ID, при необходимости поправить модель
python main.py
```

Откройте бота в Telegram: `/start` покажет приветствие, любой обычный текст уйдёт в DeepSeek, а ответ (по базе знаний студии) придёт в чат.

Изменить ответы бота: правьте `knowledge/personal_master.md` (факты) или `prompts/system_prompt.md` (манера и правила) и перезапустите бота.

## Тесты

```bash
pip install pytest
python -m pytest
```

## Этапы

- [x] 1. Каркас: бот отвечает на `/start`
- [x] 2. Постоянное меню и витрина услуг из базы знаний
- [x] 3a. Обычный текст отправляется в нейросеть (сначала DeepSeek)
- [x] 3b. База знаний и системный промпт: отвечать только по услугам студии
- [x] 3c. Ограничители: только услуги и портфолио, защита от взлома промпта
- [x] 3d. Используется DeepSeek как основной AI-провайдер
- [x] 4. Заявка на связь: кнопка «Связаться с мастером», уведомление владельцу
- [x] 5a. Корзина и оформление заказа (SQLite, статус «ожидает оплаты»)
- [ ] 5b. Тестовая оплата ЮKassa
- [ ] 6. Деплой на VPS
