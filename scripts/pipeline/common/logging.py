import json
import logging
import os
from datetime import UTC, datetime
from typing import Any


_STANDARD_LOG_RECORD_FIELDS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
_STANDARD_LOG_RECORD_FIELDS.update({"asctime", "message"})

_CONFIGURED = False
_JSON_SCALAR_TYPES = (str, int, float, bool)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, _JSON_SCALAR_TYPES):
        return value

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}

    return str(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, UTC).isoformat().replace("+00:00", "Z")
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "script": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_FIELDS or key.startswith("_"):
                continue

            payload[key] = _json_safe(value)

        return json.dumps(payload, separators=(",", ":"))


def _configure_logging() -> None:
    global _CONFIGURED

    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name)
