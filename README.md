# TSTLAN web platform

Веб-платформа мониторинга измерительных приборов по протоколу TSTLAN:
браузер ⇄ Python-сервер ⇄ приборы. Замена настольного TSTLAN. Тема ВКР;
обоснование и проектирование — в `report.typ`.

Стек: фронтенд на Next.js (`web/tstlan-web`) ⇄ FastAPI (асинхронный) ⇄
SQLAlchemy ⇄ SQLite или PostgreSQL.

## Требования

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js ≥ 20 и [pnpm](https://pnpm.io/) — для фронтенда

## Запуск (dev)

Бэкенд и фронтенд поднимаются раздельно; дефолты согласованы, поэтому
переменные окружения не нужны.

**1. Один раз — создать администратора** (команда сама прогоняет миграции):

```sh
uv run python -m tstlan.tools.create_admin --login admin --password secret
```

Создаёт `tstlan.db` со схемой и пользователя-админа. Нужна только схема без
пользователя — `make migrate`.

**2. Бэкенд** (терминал 1):

```sh
uv run tstlan                       # 127.0.0.1:8000
uv run tstlan --port 9000 --log-level DEBUG
python -m tstlan                    # эквивалентно
```

**3. Фронтенд** (терминал 2):

```sh
cd web/tstlan-web
pnpm install                        # один раз
pnpm dev                            # localhost:3000
```

**4. Открыть** `http://localhost:3000` → редирект на `/login` → войти
`admin` / `secret`.

Браузер ходит только на origin фронтенда; Next проксирует `/api/*` на бэкенд
(`BACKEND_ORIGIN`, по умолчанию `http://127.0.0.1:8000`) — для браузера это
один origin, поэтому сессионные cookie и CSRF работают без CORS. Если бэкенд
на другом порту: `BACKEND_ORIGIN=http://127.0.0.1:9000 pnpm dev`.

## База данных и миграции

По умолчанию SQLite (`./tstlan.db`); PostgreSQL — через `--database-url`
(`postgresql+psycopg://...`). Схема — источником истины является Alembic,
приложение само таблицы не создаёт.

```sh
make migrate                        # alembic upgrade head
uv run alembic revision --autogenerate -m "..."   # новая миграция
```

## Конфигурация

Приоритет: дефолты < `config.toml` < аргументы CLI
(`--host`, `--port`, `--log-level`, `--config`, `--database-url`).

Необязательный `config.toml` рядом с запуском:

```toml
bind_host = "127.0.0.1"
bind_port = 8000
log_level = "INFO"
database_url = "sqlite+aiosqlite:///./tstlan.db"
session_ttl_hours = 720             # время жизни сессии (скользящее)
session_refresh_hours = 24          # как часто продлять сессию в БД
cookie_secure = false               # в проде (HTTPS) выставить true
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
```

## Аутентификация

Сессии на сервере (таблица `sessions`), пароли — argon2. Аутентификация и
защита от CSRF вынесены в middleware: `HttpOnly`+`SameSite=Lax` cookie,
проверка `Origin` по `allowed_origins` и синхронизатор-токен
(`X-CSRF-Token` == токен сессии) на изменяющих запросах. Сессия скользящая —
продлевается при активности.

Эндпоинты:

- `GET /health` — проверка живости.
- `POST /auth/login` — `{login, password}` → `{login, role, csrf_token}`,
  ставит сессионную cookie.
- `POST /auth/logout` — отзывает сессию (нужен заголовок `X-CSRF-Token`).
- `GET /auth/me` — текущий пользователь и csrf-токен.

## Разработка

```sh
make test         # pytest
make format       # ruff format + ruff check --fix
make can-i-push   # ruff (format+check) + ty + pytest
make migrate      # alembic upgrade head
```

Фронтенд (`web/tstlan-web`):

```sh
pnpm lint
pnpm typecheck
pnpm build
```
