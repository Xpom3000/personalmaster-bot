"""Ограничители бота: проверка входа, лимит частоты, проверка выхода.

Модель — не единственная защита. Очевидные попытки взлома отсекаются кодом
до обращения к модели (это быстро и не нагружает сервер), а ответ модели проверяется
на утечку системного промпта перед отправкой клиенту.
"""
import logging
import re
import time
from collections import defaultdict, deque

MAX_INPUT_CHARS = 1000
RATE_LIMIT_MESSAGES = 10   # сообщений
RATE_LIMIT_WINDOW = 60     # за столько секунд
LEAK_NGRAM = 10            # столько слов подряд из инструкций считаем утечкой
CANARY = "PM-7F3A-GUARD"   # метка из системного промпта; в ответе быть не должна

REFUSAL_INJECTION = (
    "Я консультирую только по услугам и портфолио студии «Персональный мастер» "
    "и не могу менять свои правила или делиться служебной информацией. "
    "Готов ответить на вопросы об услугах, ценах и записи."
)
REFUSAL_OUTPUT = (
    "К сожалению, я не могу ответить на этот вопрос. "
    "Готов помочь с вопросами об услугах, ценах и записи в студию «Персональный мастер»."
)
TOO_LONG = "Сообщение слишком длинное. Пожалуйста, сформулируйте вопрос короче."
TOO_FAST = "Вы отправляете сообщения слишком часто. Пожалуйста, подождите минуту и напишите снова."

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")

# Осторожные шаблоны: лучше пропустить хитрый обход (его поймает промпт),
# чем заблокировать обычного клиента.
_INJECTION_PATTERNS = [
    # «игнорируй / забудь инструкции, правила»
    r"(игнорир|забуд|не учитывай|сбрось|обойди|нарушь|не следуй).{0,40}(инструкц|правил|ограничен|указани)",
    r"(ignore|forget|disregard|override|bypass|disable).{0,40}(instruction|rules|prompt|guideline|restriction|policies)",
    # «покажи промпт / инструкции»
    r"промпт|system\s*prompt|system\s*message|initial\s*prompt|your\s*instructions",
    r"(покаж|выведи|выдай|напиши|повтор|расскаж|раскр|пришли|скинь|процитир|перескаж|озвуч|скажи).{0,50}(свои|твои|ваши|исходн\w*|скрыт\w*|служебн\w*|системн\w*) (инструкц|указани|настройк)",
    # смена роли
    r"отныне ты",
    r"притворись",
    r"представь(те)?,? что (ты|вы)",
    r"веди себя как",
    r"действуй как",
    r"играй роль",
    r"you are now",
    r"pretend (to be|you)",
    r"act as (a|an|if)",
    r"\bdan\b",
    r"developer mode|god mode|jailbreak|джейлбрейк|режим разработчика",
]
_INJECTION_RE = [re.compile(p) for p in _INJECTION_PATTERNS]


def _normalize(text: str) -> str:
    text = _ZERO_WIDTH.sub("", text).lower().replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


def is_injection_attempt(text: str) -> bool:
    """True, если сообщение похоже на попытку обойти правила или выудить промпт."""
    norm = _normalize(text)
    return any(rx.search(norm) for rx in _INJECTION_RE)


class RateLimiter:
    """Не более `limit` сообщений от одного пользователя за `window` секунд."""

    def __init__(self, limit=RATE_LIMIT_MESSAGES, window=RATE_LIMIT_WINDOW, clock=time.monotonic):
        self._limit, self._window, self._clock = limit, window, clock
        self._hits: dict[int, deque] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = self._clock()
        hits = self._hits[user_id]
        while hits and now - hits[0] > self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", _normalize(text))


class LeakDetector:
    """Ловит ответы, в которых модель повторила служебные инструкции.

    Сверяются только инструкции (всё до раздела «База знаний:»). Факты из
    базы знаний клиентам рассказывать можно, поэтому они не проверяются.
    """

    def __init__(self, system_prompt: str, n: int = LEAK_NGRAM):
        self._n = n
        instructions = system_prompt.rsplit("База знаний:", 1)[0]
        words = _words(instructions)
        self._ngrams = {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}

    def leaks(self, answer: str) -> bool:
        if CANARY.lower() in answer.lower():
            return True
        words = _words(answer)
        return any(tuple(words[i : i + self._n]) in self._ngrams for i in range(len(words) - self._n + 1))


def filter_output(answer: str, detector: LeakDetector) -> str:
    """Вернуть ответ модели или безопасную замену, если он раскрывает инструкции."""
    if detector.leaks(answer):
        logging.warning("Ответ модели похож на утечку инструкций — заменён")
        return REFUSAL_OUTPUT
    return answer
