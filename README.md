# TSTLAN web platform

Веб-платформа мониторинга измерительных приборов по протоколу TSTLAN:
браузер ⇄ Python-сервер ⇄ приборы. Замена настольного TSTLAN. Тема ВКР;
обоснование и проектирование — в `report.typ`.

## Требования

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/)

## Запуск

```sh
uv run tstlan            # сервер на 127.0.0.1:8000
uv run tstlan --port 9000 --log-level DEBUG
python -m tstlan         # эквивалентно
```

Приоритет настроек: дефолты < `config.toml` < аргументы CLI
(`--host`, `--port`, `--log-level`, `--config`).

## Конфигурация

Необязательный `config.toml` рядом с запуском (при отсутствии — дефолты):

```toml
bind_host = "127.0.0.1"
bind_port = 8000
log_level = "INFO"
```

## Эндпоинты

- `GET /health` — проверка живости.
- `GET /var`, `POST /var` — прототипный срез чтения/записи переменной
  (заглушка до реализации протокола и устройств).

## Разработка

```sh
make test         # pytest
make format       # ruff format + ruff check --fix
make can-i-push   # ruff (format+check) + ty + pytest
```
