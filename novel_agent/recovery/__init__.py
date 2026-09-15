"""INKREST Reliability & Recovery package (Milestone B).

Provides:
- Crash recovery & non-destructive draft restoration
- Project health check & auto-repair
- Standard .inkrest-vault backup format with SHA-256 verification
- Pre-upgrade snapshots
- Diagnostic package generation with automated desensitization
"""

from novel_agent.recovery.crash_recovery import (
    CrashRecoveryManager,
    UnsavedDraft,
    CrashReport,
)
from novel_agent.recovery.health_check import (
    ProjectHealthChecker,
    HealthCheckResult,
    HealthReport,
)
from novel_agent.recovery.backup import (
    BackupManager,
    BackupManifest,
)
from novel_agent.recovery.diagnostics import (
    DiagnosticManager,
)

__all__ = [
    "CrashRecoveryManager",
    "UnsavedDraft",
    "CrashReport",
    "ProjectHealthChecker",
    "HealthCheckResult",
    "HealthReport",
    "BackupManager",
    "BackupManifest",
    "DiagnosticManager",
]
