"""Centralized logging configuration for novel_agent."""

import logging
import logging.handlers
import json
from pathlib import Path


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(log_dir: Path = None, level: int = logging.INFO) -> None:
    log_dir = Path(log_dir) if log_dir else Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("novel_agent")
    root.setLevel(level)

    if root.handlers:
        return

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "novel_agent.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"novel_agent.{name}")
