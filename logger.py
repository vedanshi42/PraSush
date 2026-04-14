from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"prasush_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_LEVEL = os.getenv("PRA_SUSH_LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in logging._nameToLevel:
    LOG_LEVEL = "INFO"

logging.basicConfig(
    level=logging._nameToLevel[LOG_LEVEL],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)

_logger = logging.getLogger("PraSush")

class AppLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, message: str, *args, **kwargs) -> None:
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        self._logger.exception(message, *args, **kwargs)

    def llm_request(self, prompt: str) -> None:
        self._logger.debug(f"LLM Request: {prompt}")

    def llm_response(self, response: str) -> None:
        self._logger.debug(f"LLM Response: {response}")

    def __getattr__(self, name: str):
        return getattr(self._logger, name)

app_logger = AppLogger(_logger)
