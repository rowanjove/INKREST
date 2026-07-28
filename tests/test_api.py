"""API integration tests — implementation split under tests/api/."""

from tests.api.test_api_chapters import ApiChaptersTests  # noqa: F401
from tests.api.test_api_config import ApiConfigTests  # noqa: F401
from tests.api.test_api_misc import ApiMiscTests  # noqa: F401
from tests.api.test_api_projects import ApiProjectsTests  # noqa: F401
from tests.api.test_api_tasks import ApiTasksTests  # noqa: F401

# Backward-compatible alias for external importers
from tests.api._base import ApiTestBase as ApiTests  # noqa: F401