import json
import logging
from unittest.mock import patch

from tstlan.auth.models import Role
from tstlan.logging_setup import JsonFormatter, get_service_logger, log_event


def test_json_formatter_includes_structured_fields() -> None:
    record = logging.LogRecord(
        name="tstlan.services.auth",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="auth.login.accepted",
        args=(),
        exc_info=None,
    )
    record.event = "auth.login.accepted"
    record.login = "alice"
    record.role = Role.ADMIN

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "auth.login.accepted"
    assert payload["service"] == "auth"
    assert payload["event"] == "auth.login.accepted"
    assert payload["login"] == "alice"
    assert payload["role"] == "admin"


def test_service_logger_uses_service_namespace() -> None:
    logger = get_service_logger("configs")
    assert logger.name == "tstlan.services.configs"

    with patch.object(logger, "log") as mocked_log:
        log_event(logger, logging.INFO, "configs.created", config_id=1)

    mocked_log.assert_called_once_with(
        logging.INFO,
        "configs.created",
        extra={"event": "configs.created", "config_id": 1},
    )
