"""Deprecated root orchestrator entry point. Use cli.py instead."""

import sys
import warnings
from cli import _normalize_argv

def main() -> None:
    warnings.warn(
        "根目录下的 orchestrator.py 已被废弃，命令行入口已整合至 cli.py。本次执行已自动重定向至 cli.py。",
        DeprecationWarning,
        stacklevel=2,
    )
    print(
        "WARNING: Root orchestrator.py is deprecated. Redirecting execution to cli.py...\n",
        file=sys.stderr,
    )
    import cli
    cli.main()


if __name__ == "__main__":
    main()
