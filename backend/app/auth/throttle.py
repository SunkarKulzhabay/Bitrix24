import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

# Неудачные попытки по паре «адрес компьютера + логин». Хранится в памяти:
# при перезапуске сервера счётчики сбрасываются.
_failures: dict[str, deque] = defaultdict(deque)


def _key(request: Request, login: str) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{ip}|{login}"


def _prune(entries: deque, now: float) -> None:
    while entries and now - entries[0] > WINDOW_SECONDS:
        entries.popleft()


def check_allowed(request: Request, login: str) -> None:
    key = _key(request, login)
    entries = _failures.get(key)
    if entries is None:
        return

    now = time.monotonic()
    _prune(entries, now)
    if not entries:
        del _failures[key]
        return

    if len(entries) >= MAX_ATTEMPTS:
        minutes = int((WINDOW_SECONDS - (now - entries[0])) // 60) + 1
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Слишком много неудачных попыток. Попробуйте через {minutes} мин.",
        )


def register_failure(request: Request, login: str) -> None:
    now = time.monotonic()
    # Чтобы память не росла бесконечно, изредка убираем устаревшие записи
    if len(_failures) > 10000:
        for key in list(_failures):
            _prune(_failures[key], now)
            if not _failures[key]:
                del _failures[key]
    _failures[_key(request, login)].append(now)


def reset(request: Request, login: str) -> None:
    _failures.pop(_key(request, login), None)