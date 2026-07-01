import json
import logging
from datetime import UTC, datetime
from typing import Any

_BASE_RECORD_KEYS = frozenset(logging.makeLogRecord({}).__dict__)
_PAYLOAD_KEYS = frozenset({"timestamp", "level", "logger", "message"})
_SERVICE_LOGGER_PREFIX = "tstlan.services."


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        service = _service_name(record.name)
        if service is not None:
            payload["service"] = service
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def init_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_service_logger(service: str) -> logging.Logger:
    return logging.getLogger(f"{_SERVICE_LOGGER_PREFIX}{service}")


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"event": event, **fields})


def _extra_fields(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _BASE_RECORD_KEYS
        and key not in _PAYLOAD_KEYS
        and not key.startswith("_")
    }


def _service_name(logger_name: str) -> str | None:
    if logger_name.startswith(_SERVICE_LOGGER_PREFIX):
        return logger_name.removeprefix(_SERVICE_LOGGER_PREFIX).split(".", maxsplit=1)[
            0
        ]
    return None
