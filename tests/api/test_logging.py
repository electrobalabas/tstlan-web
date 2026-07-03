import json
import logging

from tstlan.auth.models import Role
from tstlan.logging_setup import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.LogRecord(
        name="tstlan.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event happened",
        args=(),
        exc_info=None,
    )
    record.login = "alice"
    record.role = Role.ADMIN

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "event happened"
    assert payload["login"] == "alice"
    assert payload["role"] == "admin"
