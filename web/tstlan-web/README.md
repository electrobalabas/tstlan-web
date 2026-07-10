# TSTLAN frontend

Frontend TSTLAN находится в `web/tstlan-web` и работает на Next.js.
Он не запускается сам по себе: для полноценной работы нужен backend из корня
репозитория.

## Первый запуск

Из корня репозитория сначала подготовьте backend:

```sh
uv run python -m tstlan.tools.create_admin --login admin --password secret
uv run tstlan
```

Затем в отдельном терминале:

```sh
cd web/tstlan-web
pnpm install
pnpm dev
```

Откройте `http://localhost:3000` и войдите:

- login: `admin`
- password: `secret`

## Связь с backend

Next.js проксирует `/api/*` на backend. По умолчанию используется
`http://127.0.0.1:8000`.

Если backend запущен на другом адресе:

```sh
BACKEND_ORIGIN=http://127.0.0.1:9000 pnpm dev
```

PowerShell:

```powershell
$env:BACKEND_ORIGIN = "http://127.0.0.1:9000"
pnpm dev
```

## Команды разработки

```sh
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

`pnpm install` нужно выполнять один раз после клонирования репозитория и после
изменения `pnpm-lock.yaml`.
