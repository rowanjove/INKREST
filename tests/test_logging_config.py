import logging
import tempfile
import unittest
from pathlib import Path

from novel_agent.logging_config import setup_logging, shutdown_logging


class LoggingLifecycleTests(unittest.TestCase):
    def tearDown(self):
        shutdown_logging()

    def test_shutdown_closes_managed_file_handler(self):
        with tempfile.TemporaryDirectory(prefix="novel-agent-logging-") as tmp:
            log_dir = Path(tmp)
            setup_logging(log_dir)
            logging.getLogger("novel_agent.test").info("flush me")

            shutdown_logging()

            log_path = log_dir / "novel_agent.log"
            self.assertIn("flush me", log_path.read_text(encoding="utf-8"))
            log_path.unlink()
            self.assertFalse(log_path.exists())

    def test_setup_does_not_duplicate_managed_handlers(self):
        with tempfile.TemporaryDirectory(prefix="novel-agent-logging-") as tmp:
            setup_logging(Path(tmp))
            setup_logging(Path(tmp))
            managed = [
                handler
                for handler in logging.getLogger("novel_agent").handlers
                if getattr(handler, "_novel_agent_managed", False)
            ]

            self.assertEqual(len(managed), 2)
            shutdown_logging()
