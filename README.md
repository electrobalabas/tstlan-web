# TSTLAN web platform

TSTLAN - веб-платформа мониторинга измерительных приборов:
браузер -> Next.js frontend -> FastAPI backend -> приборы. Проект можно
запустить локально без внешней базы и без реального оборудования: по умолчанию
используется SQLite и встроенная симуляция приборов.

## Что нужно установить

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/) для Python-зависимостей и запуска backend
- Node.js >= 20
- pnpm для frontend

Быстрая установка инструментов:

```sh
# Python runtime для проекта, если 3.14 ещё нет в системе
uv python install 3.14

# pnpm через Corepack, который идёт вместе с Node.js
corepack enable
corepack prepare pnpm@latest --activate
```

Проверка:

```sh
uv --version
python --version
node --version
pnpm --version
```

## Первый запуск

Команды ниже выполняются из корня репозитория, кроме frontend-команд.

### 1. Создать базу и администратора

```sh
uv run python -m tstlan.tools.create_admin --login admin --password secret
```

Команда сама установит Python-зависимости через `uv`, применит миграции Alembic
и создаст локальный `tstlan.db`. Повторный запуск с тем же логином завершится
ошибкой, потому что пользователь уже есть.

### 2. Запустить backend

Откройте первый терминал:

```sh
uv run tstlan
```

Backend будет доступен на `http://127.0.0.1:8000`.

Проверка:

```sh
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

### 3. Запустить frontend

Откройте второй терминал:

```sh
cd web/tstlan-web
pnpm install
pnpm dev
```

Frontend будет доступен на `http://localhost:3000`.

Откройте страницу в браузере и войдите:

- login: `admin`
- password: `secret`

Next.js проксирует `/api/*` на backend. По умолчанию используется
`http://127.0.0.1:8000`, поэтому дополнительные переменные окружения для
обычного запуска не нужны.

## Запуск с тестовыми данными и внешними dev-приборами

Обычный `uv run tstlan` запускает приборы in-process. Если нужно проверить
режим, где приборы вынесены в отдельные TCP-процессы, используйте
`config.dev.toml`.

Откройте отдельные терминалы:

```sh
make device-multimeter
make device-thermostat
make dev-server
```

После запуска backend можно наполнить базу тестовыми пользователями и
конфигами:

```sh
make seed
```

Тестовые пользователи:

- `admin` / `admin123`
- `engineer` / `engineer123`
- `operator` / `operator123`
- `viewer` / `viewer123`

`make seed` ходит в уже запущенный backend через HTTP API, поэтому backend
должен работать до запуска этой команды.

## Частые проблемы

### `pnpm` не найден

Включите Corepack:

```sh
corepack enable
corepack prepare pnpm@latest --activate
```

### Backend запущен не на 8000 порту

Запустите frontend с явным адресом backend:

```sh
cd web/tstlan-web
BACKEND_ORIGIN=http://127.0.0.1:9000 pnpm dev
```

На Windows PowerShell:

```powershell
cd web/tstlan-web
$env:BACKEND_ORIGIN = "http://127.0.0.1:9000"
pnpm dev
```

### Нужно пересоздать локальную SQLite-базу

Остановите backend, удалите `tstlan.db`, затем заново создайте администратора:

```sh
uv run python -m tstlan.tools.create_admin --login admin --password secret
```

### Порт уже занят

Backend можно запустить на другом порту:

```sh
uv run tstlan --port 9000
```

После этого frontend тоже нужно направить на новый порт через
`BACKEND_ORIGIN`.

## Разработка

```sh
make test           # unit-тесты
make coverage       # тесты + coverage report
make format         # ruff format + ruff check --fix
make can-i-push     # format check + ruff + ty + pytest
make migrate        # alembic upgrade head
make docs-build     # собрать HTML-документацию
```

Опциональные проверки:

```sh
make test-integration       # TCP-интеграция с devsim
make test-postgres          # PostgreSQL-тесты через docker compose
make postgres-down          # остановить PostgreSQL compose
```

## Документация

Подробные инструкции лежат в `docs/`.

```sh
make docs-build
make docs-open
```

Основной файл для запуска и эксплуатации:
`docs/operations.rst`.
