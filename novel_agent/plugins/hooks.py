"""Hook specifications, contracts, and runner for INKREST Plugin Platform 2.0.

Inspired by pytest/pluggy architecture:
- Hook Specification (@hookspec) defines the signature and contract
- Hook Implementation (@hookimpl) provides the plugin logic
- HookContract enforces execution mode (collect, first, reduce), timeouts, and failure policies
"""

from __future__ import annotations

import functools
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class HookError(Exception):
    """Base exception for hook failures."""
    pass


class HookExecutionError(HookError):
    pass


class HookTimeoutError(HookError):
    pass


@dataclass
class HookContract:
    name: str
    mode: str = "collect"  # collect, first, reduce
    timeout: float = 5.0
    failure_policy: str = "skip"  # skip, retry, fail, fallback
    parallel: bool = False
    priority: int = 0
    fallback_value: Any = None


def hookspec(
    func: Optional[Callable[..., Any]] = None,
    *,
    mode: str = "collect",
    timeout: float = 5.0,
    failure: str = "skip",
    parallel: bool = False,
    priority: int = 0,
    fallback_value: Any = None,
) -> Any:
    """Decorator marking a function as a Hook Specification."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        contract = HookContract(
            name=fn.__name__,
            mode=mode,
            timeout=timeout,
            failure_policy=failure,
            parallel=parallel,
            priority=priority,
            fallback_value=fallback_value,
        )
        fn.__hookspec__ = contract  # type: ignore[attr-defined]
        return fn

    if func is not None and callable(func):
        return decorator(func)
    return decorator


def hookimpl(
    func: Optional[Callable[..., Any]] = None,
    *,
    priority: int = 0,
    optionalhook: bool = False,
) -> Any:
    """Decorator marking a function as a Hook Implementation."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.__hookimpl__ = {  # type: ignore[attr-defined]
            "priority": priority,
            "optionalhook": optionalhook,
        }
        return fn

    if func is not None and callable(func):
        return decorator(func)
    return decorator


@dataclass
class RegisteredHookImpl:
    plugin_id: str
    func: Callable[..., Any]
    priority: int = 0


class HookRegistry:
    """Manages hook specifications and registered implementations."""

    def __init__(self) -> None:
        self.specs: Dict[str, HookContract] = {}
        self.impls: Dict[str, List[RegisteredHookImpl]] = {}

    def register_spec(self, spec_fn: Callable[..., Any]) -> HookContract:
        contract = getattr(spec_fn, "__hookspec__", None)
        if not contract:
            contract = HookContract(name=spec_fn.__name__)
        self.specs[contract.name] = contract
        return contract

    def register_impl(
        self,
        hook_name: str,
        plugin_id: str,
        impl_fn: Callable[..., Any],
        priority: Optional[int] = None,
    ) -> None:
        impl_meta = getattr(impl_fn, "__hookimpl__", {})
        prio = priority if priority is not None else impl_meta.get("priority", 0)
        entry = RegisteredHookImpl(plugin_id=plugin_id, func=impl_fn, priority=prio)
        self.impls.setdefault(hook_name, []).append(entry)
        self.impls[hook_name].sort(key=lambda x: x.priority, reverse=True)

    def unregister_plugin_hooks(self, plugin_id: str) -> None:
        for name in list(self.impls.keys()):
            self.impls[name] = [impl for impl in self.impls[name] if impl.plugin_id != plugin_id]

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        """Call a hook according to its contract specification."""
        contract = self.specs.get(hook_name, HookContract(name=hook_name))
        implementations = self.impls.get(hook_name, [])

        if not implementations:
            if contract.mode == "reduce" and args:
                return args[0]
            if contract.mode == "collect":
                return []
            return contract.fallback_value

        if contract.mode == "collect":
            results = []
            for impl in implementations:
                res = self._execute_single_impl(impl, contract, *args, **kwargs)
                if res is not None:
                    results.append(res)
            return results

        elif contract.mode == "first":
            for impl in implementations:
                res = self._execute_single_impl(impl, contract, *args, **kwargs)
                if res is not None:
                    return res
            return contract.fallback_value

        elif contract.mode == "reduce":
            current_value = args[0] if args else kwargs.get("initial_value")
            rest_args = args[1:] if len(args) > 1 else ()
            for impl in implementations:
                res = self._execute_single_impl(impl, contract, current_value, *rest_args, **kwargs)
                if res is not None:
                    current_value = res
            return current_value

        return None

    def _execute_single_impl(
        self, impl: RegisteredHookImpl, contract: HookContract, *args: Any, **kwargs: Any
    ) -> Any:
        try:
            start_time = time.time()
            res = impl.func(*args, **kwargs)
            duration = time.time() - start_time
            if duration > contract.timeout:
                if contract.failure_policy == "fail":
                    raise HookTimeoutError(
                        f"Hook '{contract.name}' by '{impl.plugin_id}' timed out ({duration:.2f}s > {contract.timeout}s)"
                    )
            return res
        except Exception as exc:
            if contract.failure_policy == "fail":
                raise HookExecutionError(f"Hook '{contract.name}' failed in '{impl.plugin_id}': {exc}") from exc
            # For 'skip' or 'fallback', return fallback_value or None
            return contract.fallback_value
