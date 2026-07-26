<div align="center">
    <h1>⚡ fastapi-sliding-window</h1>
    <a href="https://pypi.org/project/fastapi-sliding-window/">
        <img alt="PyPI version" src="https://img.shields.io/pypi/v/fastapi-sliding-window?color=blue">
    </a>
    <img height="20" alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10+-blue">
    <img height="20" alt="License MIT" src="https://img.shields.io/badge/license-MIT-green">
    <img height="20" alt="Status" src="https://img.shields.io/badge/status-stable-brightgreen">
    <p><strong>fastapi-sliding-window</strong> — sliding window rate limiter for FastAPI</p>
    <blockquote>(─‿‿─)</blockquote>
</div>

---

```
 ,---.                ,--.                 ,--. 
/  .-' ,--,--. ,---.,-'  '-. ,--,--. ,---. `--' 
|  `-,' ,-.  |(  .-''-.  .-'' ,-.  || .-. |,--. 
|  .-'\ '-'  |.-'  `) |  |  \ '-'  || '-' '|  | 
`--'   `--`--'`----'  `--'   `--`--'|  |-' `--' 
                                    `--'        
                                                                 
                 ,--.             ,--.,--.          ,--.  ,--.   
,--.--. ,--,--.,-'  '-. ,---.     |  |`--',--,--,--.`--',-'  '-. 
|  .--'' ,-.  |'-.  .-'| .-. :    |  |,--.|        |,--.'-.  .-' 
|  |   \ '-'  |  |  |  \   --.    |  ||  ||  |  |  ||  |  |  |   
`--'    `--`--'  `--'   `----'    `--'`--'`--`--`--'`--'  `--'   
```

## **📦 установка**

```bash
pip install fastapi-sliding-window
```

---

## **📑 быстрый старт**

```python
from fastapi import FastAPI, Depends
from fastapi_sliding_window import RateLimit

app = FastAPI()

@app.get("/login", dependencies=[Depends(RateLimit(requests=5, window_seconds=60))])
async def login():
    return {"status": "ok"}
```

---

## **🧩 возможности**

- 🎯 **3 алгоритма** — Sliding Window Log (точный), Sliding Window Counter (O(1) память), Fixed Window
- 💾 **в памяти** — не требует Redis, нулевые внешние зависимости
- 🔧 **два стиля использования** — `Depends(RateLimit(...))` per-route или `RateLimitMiddleware` глобально
- 📝 **стандартные заголовки** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- ✅ **полная типизация** — `py.typed` маркер включён
- 🚀 **async-native** — построен на `asyncio.Lock` для потокобезопасности

---

## **📖 использование**

### Depends (per-route)

```python
from fastapi import Depends
from fastapi_sliding_window import RateLimit, Algorithm

# Sliding Window Log (по умолчанию, максимальная точность)
@app.get("/api/data", dependencies=[
    Depends(RateLimit(requests=100, window_seconds=60))
])
async def get_data():
    return {"data": "..."}

# Fixed Window (самый быстрый, O(1) память)
@app.post("/api/upload", dependencies=[
    Depends(RateLimit(requests=10, window_seconds=60, algorithm=Algorithm.FIXED_WINDOW))
])
async def upload():
    return {"status": "uploaded"}

# кастомная функция ключа (per-user вместо per-IP)
async def user_key(request):
    return request.headers.get("X-User-ID", "anonymous")

@app.get("/api/profile", dependencies=[
    Depends(RateLimit(requests=50, window_seconds=60, key_func=user_key))
])
async def profile():
    return {"user": "..."}
```

### Middleware (глобальный)

```python
from fastapi_sliding_window import RateLimitMiddleware, Algorithm

app.add_middleware(
    RateLimitMiddleware,
    requests=100,
    window_seconds=60.0,
    algorithm=Algorithm.SLIDING_WINDOW_LOG,
    exclude_paths=["/health"],  # пропустить rate limiting для этих путей
)
```

---

## **📊 алгоритмы**

| Алгоритм | Точность | Память | Скорость | Для чего |
|----------|----------|--------|----------|----------|
| **Sliding Window Log** | 100% | O(requests/window) | O(1) amortized | критичные к точности эндпоинты |
| **Sliding Window Counter** | ~99% | O(1) на ключ | O(1) | высоконагруженные API |
| **Fixed Window** | ~50% (boundary burst) | O(1) на ключ | O(1) | простые квоты |

### Sliding Window Log

Хранит таймстемп каждого запроса. Очищает записи за пределами окна при каждой проверке. Идеально точный, память растёт линейно с объёмом запросов в окне.

### Sliding Window Counter

Поддерживает два счётчика (текущее и предыдущее окно) и вычисляет взвешенное среднее. Почти точный с постоянным памятью. Лучший баланс точности и производительности.

### Fixed Window

Простой счётчик на временной интервал. Страдает от boundary burst (клиент может отправить 2x лимит через границу окна).

---

## **📝 HTTP заголовки**

при успешном запросе ответ содержит:

| Заголовок | Описание |
|-----------|----------|
| `X-RateLimit-Limit` | максимальное количество запросов |
| `X-RateLimit-Remaining` | оставшиеся запросы в окне |
| `X-RateLimit-Reset` | unix timestamp сброса окна |
| `Retry-After` | секунды до следующего разрешённого запроса (429, только middleware) |

---

## **🔗 API Reference**

### `RateLimit(requests, window_seconds, algorithm, key_func, include_headers)`

FastAPI dependency для per-route rate limiting.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `requests` | `int` | обязательный | макс. запросов за окно |
| `window_seconds` | `float` | обязательный | длительность окна в секундах |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | алгоритм rate limiting |
| `key_func` | `KeyFunc` | IP-адрес | функция извлечения ключа клиента |
| `include_headers` | `bool` | `True` | добавлять заголовки rate limit |

### `RateLimitMiddleware(requests, window_seconds, algorithm, key_func, include_headers, exclude_paths)`

Starlette middleware для глобального rate limiting.

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `requests` | `int` | `100` | макс. запросов за окно |
| `window_seconds` | `float` | `60.0` | длительность окна в секундах |
| `algorithm` | `Algorithm` | `SLIDING_WINDOW_LOG` | алгоритм rate limiting |
| `key_func` | `KeyFunc` | IP-адрес | функция извлечения ключа клиента |
| `include_headers` | `bool` | `True` | добавлять заголовки rate limit |
| `exclude_paths` | `list[str]` | `None` | пути без rate limiting |

---

## **📜 лицензия**
[MIT](https://github.com/drawiks/fastapi-sliding-window/blob/main/LICENSE)
