"""Subprocess Worker for isolated plugin execution."""

from __future__ import annotations

import importlib.util
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from novel_agent.plugins.runtime.rpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    RPCError,
    RPCRequest,
    RPCResponse,
    decode_message,
)


def _load_plugin_instance(entry_str: str, plugin_root: Optional[Path] = None) -> Any:
    """Load and instantiate a plugin instance from an entry spec (e.g. 'plugin:PluginClass')."""
    if ":" not in entry_str:
        raise ValueError(f"Invalid entry specification: '{entry_str}'. Expected 'module:Class'")

    mod_name, class_name = entry_str.split(":", 1)

    if plugin_root and (plugin_root / f"{mod_name}.py").is_file():
        file_path = plugin_root / f"{mod_name}.py"
        spec = importlib.util.spec_from_file_location(mod_name, file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load module spec from {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(mod_name)

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(f"Class '{class_name}' not found in module '{mod_name}'")

    return cls()


def worker_process_main(
    in_queue: mp.Queue,
    out_queue: mp.Queue,
    plugin_id: str,
    entry_str: str = "",
    plugin_root_str: str = "",
) -> None:
    """Entrypoint running inside the isolated subprocess worker."""
    plugin_instance: Optional[Any] = None
    plugin_root = Path(plugin_root_str) if plugin_root_str else None

    # Pre-load if entry provided
    if entry_str:
        try:
            plugin_instance = _load_plugin_instance(entry_str, plugin_root)
        except Exception as exc:
            out_queue.put(
                RPCResponse(
                    id="init",
                    error=RPCError(code=INTERNAL_ERROR, message=f"Worker init failed: {exc}"),
                ).to_dict()
            )
            return

    while True:
        try:
            raw_req = in_queue.get()
            if raw_req is None:  # Sentinel to terminate
                break

            req = decode_message(raw_req)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params") or {}

            # 1. System ping
            if method == "system.ping":
                resp = RPCResponse(
                    id=req_id,
                    result={"status": "pong", "pid": os.getpid(), "timestamp": time.time()},
                )
                out_queue.put(resp.to_dict())
                continue

            # 2. System load
            if method == "system.load":
                target_entry = params.get("entry", entry_str)
                raw_root = params.get("plugin_root") or plugin_root_str
                target_root = Path(raw_root) if raw_root else None
                plugin_instance = _load_plugin_instance(target_entry, target_root)
                resp = RPCResponse(id=req_id, result={"loaded": True, "pid": os.getpid()})
                out_queue.put(resp.to_dict())
                continue

            # 3. System shutdown
            if method == "system.shutdown":
                resp = RPCResponse(id=req_id, result={"shutdown": True})
                out_queue.put(resp.to_dict())
                break

            # 4. Invoke hook / method on plugin
            if method.startswith("hook.") or method.startswith("plugin."):
                action_name = method.split(".", 1)[1]
                if not plugin_instance:
                    resp = RPCResponse(
                        id=req_id,
                        error=RPCError(code=INTERNAL_ERROR, message="Plugin instance not loaded"),
                    )
                    out_queue.put(resp.to_dict())
                    continue

                fn = getattr(plugin_instance, action_name, None)
                if not fn or not callable(fn):
                    resp = RPCResponse(
                        id=req_id,
                        error=RPCError(code=METHOD_NOT_FOUND, message=f"Method '{action_name}' not found on plugin"),
                    )
                    out_queue.put(resp.to_dict())
                    continue

                args = params.get("args", [])
                kwargs = params.get("kwargs", {})
                res = fn(*args, **kwargs)
                resp = RPCResponse(id=req_id, result=res)
                out_queue.put(resp.to_dict())
                continue

            # Default unknown method
            resp = RPCResponse(
                id=req_id,
                error=RPCError(code=METHOD_NOT_FOUND, message=f"Unknown method: '{method}'"),
            )
            out_queue.put(resp.to_dict())

        except Exception as exc:
            req_id = req.get("id") if "req" in locals() and isinstance(req, dict) else "unknown"
            err_resp = RPCResponse(
                id=req_id,
                error=RPCError(code=INTERNAL_ERROR, message=str(exc)),
            )
            out_queue.put(err_resp.to_dict())
