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

## Приборы-эмуляторы и тестовые данные

Приборы можно вынести в отдельные процессы (`devsim`): эмулятор держит буфер
прибора, крутит сигналы из профиля прибора и отдаёт значения по TCP. Бэкенд ходит
к ним клиентом, если в конфиге задан список `devices` (`config.dev.toml`); иначе
приборы поднимаются in-process с симуляцией. Соединение ленивое — прибор можно
поднять и после сервера, метаданные `GET /devices` доступны сразу.

```sh
make device-multimeter    # эмулятор на 127.0.0.1:9001 (dev/multimeter.yaml)
make device-thermostat    # эмулятор на 127.0.0.1:9002 (dev/thermostat.yaml)
make dev-server           # tstlan --config config.dev.toml (ходит к эмуляторам)
make seed                 # тестовые юзеры (напрямую в БД) + конфиги (через POST)
```

Сид (`tstlan.tools.seed`, данные — `tstlan/tools/seed_data.py`) идемпотентно
создаёт пользователей `admin`/`engineer`/`operator`/`viewer` (пароль `<login>123`)
и конфиги с разной видимостью и шарингом — чтобы прокликать приватные/общие
конфиги, права read/write и значения приборов. Запускать при поднятом сервере.

Свой прибор — это профиль прибора (`dev/*.yaml`): имя, тип, переменные (`ctype`,
`mode` r/rw/w, опционально `signal`). Запуск отдельного прибора:
`uv run python -m devsim --profile <файл> --port <порт>`.

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
make coverage     # pytest + coverage report (term/html/xml)
make test-postgres # PostgreSQL migrations against docker compose
make format       # ruff format + ruff check --fix
make can-i-push   # ruff (format+check) + ty + pytest
make migrate      # alembic upgrade head
```

PostgreSQL tests use `docker-compose.test.yml` and run only on demand:

```sh
make test-postgres
make postgres-down
```

Фронтенд (`web/tstlan-web`):

```sh
pnpm lint
pnpm typecheck
pnpm build
```
