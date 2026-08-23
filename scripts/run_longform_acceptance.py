#!/usr/bin/env python3
"""Plan or explicitly execute a bounded long-form acceptance run.

The default command is intentionally side-effect-light: it only writes a
manifest.  Actual model calls require the independent ``--start`` and
``--execute`` acknowledgements, a project root, a positive hard budget and a
pre-existing chapter queue.  The execution path keeps the manifest itself as
an atomic, redacted checkpoint so an interrupted run can be resumed without
silently changing the model configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class AcceptanceRunError(RuntimeError):
    """A preflight or immutable-run-contract failure."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_input(value: Any) -> str:
    """Digest a referenced local file by bytes, otherwise digest its value."""
    text = str(value)
    path = Path(text)
    try:
        if path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        pass
    return _digest(text)


def _digest_json(value: Any) -> str:
    return _digest(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")))


def _iter_llm_clients(client: Any) -> Iterable[Any]:
    """Yield primary/fallback clients once for runtime contract binding."""

    seen: set[int] = set()
    stack = [client]
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        primary = getattr(current, "primary", None)
        if primary is not None:
            stack.append(primary)
        for fallback in reversed(list(getattr(current, "fallbacks", []) or [])):
            stack.append(fallback)


def _client_model(client: Any) -> str:
    model = getattr(client, "model", None)
    if model:
        return str(model)
    if client.__class__.__name__ == "StaticLLM":
        return "static"
    provider = getattr(client, "provider", None)
    return str(provider or client.__class__.__name__)


def _runtime_config_digest(root: Path) -> str:
    """Digest the files that determine a project's resolved pipeline."""

    paths = [root / "config" / "pipeline.yaml", root / "config" / "models.json"]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.name).encode("utf-8"))
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"<missing>")
    return digest.hexdigest()


def _runtime_prompt_digest(root: Path) -> str:
    from novel_agent.prompt_registry import prompt_manifest

    manifest = prompt_manifest(root)
    # Exclude absolute paths so the same prompt content has the same digest
    # when a project is resumed from another checkout or drive.
    stable_roles = []
    for role in manifest.get("roles", []):
        stable_roles.append(
            {
                "role": role.get("role"),
                "selected_source": role.get("selected_source"),
                "selected_sha256": role.get("selected_sha256"),
                "canonical_sha256": role.get("canonical_sha256"),
                "has_drift": bool(role.get("has_drift")),
            }
        )
    return _digest_json({"schema_version": manifest.get("schema_version"), "roles": stable_roles})


def _bind_runtime_contract(
    args: argparse.Namespace,
    config: Any,
    root: Path,
    manifest: Dict[str, Any],
) -> Dict[str, Any]:
    """Bind the manifest to the resolved runtime, refusing silent drift.

    Injectable test factories do not necessarily expose a PipelineConfig;
    those retain the requested manifest values. Real PipelineConfig instances
    must expose the resolved model, embedding, prompt and pipeline digests.
    """

    registry = getattr(config, "llm_registry", None)
    if not isinstance(registry, Mapping) or not registry:
        return manifest

    clients = list(_iter_llm_clients(getattr(config, "llm", None)))
    if not clients:
        raise AcceptanceRunError("流水线没有可检查的 LLM client，拒绝生成验收清单")
    models = sorted({_client_model(client) for client in clients})
    default_model = _client_model(getattr(config, "llm", None))
    requested_model = getattr(args, "model", None)
    if requested_model and requested_model != "configured-model" and str(requested_model) != default_model:
        raise AcceptanceRunError(f"--model 与实际默认模型不一致：{requested_model} != {default_model}")

    temperatures = {
        round(float(getattr(client, "temperature")), 6)
        for client in clients
        if getattr(client, "temperature", None) is not None
    }
    requested_temperature = getattr(args, "temperature", None)
    if requested_temperature is not None:
        requested_temperature = float(requested_temperature)
        for client in clients:
            if hasattr(client, "temperature"):
                setattr(client, "temperature", requested_temperature)
        temperatures = {round(requested_temperature, 6)}
    actual_temperature = sorted(temperatures)[0] if len(temperatures) == 1 else None
    if actual_temperature is None:
        raise AcceptanceRunError("不同 LLM client 的 temperature 不一致，无法形成固定验收配置")

    seed = int(getattr(args, "seed", 0))
    random.seed(seed)
    seed_bound_clients: list[str] = []
    for client in clients:
        if hasattr(client, "seed") or client.__class__.__name__ == "OpenAILLM":
            setattr(client, "seed", seed)
            seed_bound_clients.append(client.__class__.__name__)

    embedding_config = getattr(config, "embedding_config", {}) or {}
    actual_embedding = str(
        embedding_config.get("model")
        or embedding_config.get("model_name")
        or embedding_config.get("provider")
        or "unknown"
    ) if isinstance(embedding_config, Mapping) else str(embedding_config)
    actual_prompt_digest = _runtime_prompt_digest(root)
    requested_prompt_digest = getattr(args, "prompt_digest", "") or ""
    if requested_prompt_digest and requested_prompt_digest != actual_prompt_digest:
        raise AcceptanceRunError("--prompt-digest 与项目实际 prompt manifest 不一致")
    requested_embedding_digest = getattr(args, "embedding_digest", "") or ""
    actual_embedding_digest = _digest_json(embedding_config)
    if requested_embedding_digest and requested_embedding_digest != actual_embedding_digest:
        raise AcceptanceRunError("--embedding-digest 与项目实际 embedding 配置不一致")
    requested_config = getattr(args, "config", None)
    actual_config_digest = _runtime_config_digest(root)
    if requested_config and requested_config != "configured-pipeline":
        requested_config_digest = _digest_input(requested_config)
        if requested_config_digest != actual_config_digest:
            raise AcceptanceRunError("--config 与项目实际 pipeline/models 配置不一致")

    manifest.update(
        {
            "model": default_model,
            "available_models": models,
            "prompt_digest": actual_prompt_digest,
            "embedding": actual_embedding,
            "embedding_digest": actual_embedding_digest,
            "config_digest": actual_config_digest,
            "seed": seed,
            "temperature": actual_temperature,
            "execution_contract": {
                "resolved": True,
                "seed_binding": "provider_payload_or_process" if seed_bound_clients else "process_only",
                "seed_clients": seed_bound_clients,
                "retrieval_comparison_status": "not_run",
            },
        }
    )
    return manifest


def _redact(value: Any, limit: int = 500) -> str:
    """Keep errors useful while avoiding keys, headers and raw prompt text."""
    text = " ".join(str(value).split())
    text = re.sub(r"(?i)(sk-[A-Za-z0-9_-]{8,}|api[_-]?key\s*[:=]\s*\S+)", "[REDACTED]", text)
    return text[:limit] + ("…" if len(text) > limit else "")


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    prompt_digest = getattr(args, "prompt_digest", "") or _digest_input(getattr(args, "prompt", None) or "default-prompt")
    embedding_value = getattr(args, "embedding", None) or "configured-embedding"
    embedding_digest = getattr(args, "embedding_digest", "") or _digest_input(embedding_value)
    execute = bool(getattr(args, "execute", False))
    return {
        "schema_version": 1,
        "run_id": f"longform-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "status": "planned",
        "launch_status": "explicit_acknowledged" if getattr(args, "start", False) else "plan_only",
        "operator_started": bool(getattr(args, "start", False)),
        "chapters": int(getattr(args, "chapters", 20)),
        "model": str(getattr(args, "model", None) or "configured-model"),
        "prompt_digest": prompt_digest,
        "embedding": str(embedding_value),
        "embedding_digest": embedding_digest,
        "config_digest": _digest_input(getattr(args, "config", None) or "configured-pipeline"),
        "seed": int(getattr(args, "seed", 0)),
        "temperature": float(getattr(args, "temperature", None) if getattr(args, "temperature", None) is not None else 0.7),
        "budget": {"max_cost_units": float(getattr(args, "budget", 0))},
        "retrieval_comparison": ["adjacent-only", "hybrid"],
        "retrieval_comparison_status": "not_run",
        "quality_check_interval": 10,
        "interruptions": [],
        "retries": [],
        "manual_samples": [],
        "completed_chapters": [],
        "failed_chapters": [],
        "chapter_results": [],
        "quality_trend": [],
        "checkpoint": {"completed_count": 0, "last_chapter_id": "", "updated_at": None},
        "cost": {"used": 0.0, "tokens": 0, "currency": "local_units"},
        "artifacts": {"raw_local_only": True, "redacted_summary": True},
        "execution": {
            "requested": execute,
            "resume": bool(getattr(args, "resume", True)),
            "max_retries": int(getattr(args, "max_retries", 1)),
        },
        "notes": "真实模型长跑必须由用户显式启动；默认不生成正文。local_units 与 SQLite total_cost_cny 同口径。",
    }


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceRunError(f"无法读取运行清单：{_redact(exc)}") from exc
    if not isinstance(data, dict):
        raise AcceptanceRunError("运行清单必须是 JSON object")
    return data


def _brief_entries(root: Path, target: int) -> List[Tuple[str, Dict[str, Any]]]:
    from novel_agent.services.arc_queue import (
        chapter_id_from_brief,
        load_workspace_arcs,
        sort_briefs_by_dependencies,
    )

    entries: List[Tuple[str, Dict[str, Any]]] = []
    seen: set[str] = set()
    for arc in load_workspace_arcs(root):
        arc_id = str(arc.get("arc_id") or "")
        for brief in sort_briefs_by_dependencies(list(arc.get("chapters") or [])):
            chapter_id = chapter_id_from_brief(brief)
            if not chapter_id or chapter_id in seen:
                continue
            seen.add(chapter_id)
            entries.append((arc_id, brief))
            if len(entries) >= target:
                return entries
    return entries


def _preflight(root: Path, target: int) -> List[Tuple[str, Dict[str, Any]]]:
    root = root.resolve()
    if not root.is_dir():
        raise AcceptanceRunError(f"项目根目录不存在：{root}")
    config_path = root / "config" / "pipeline.yaml"
    if not config_path.is_file():
        raise AcceptanceRunError(f"缺少固定流水线配置：{config_path}")
    entries = _brief_entries(root, target)
    if len(entries) < target:
        raise AcceptanceRunError(
            f"章节队列不足：需要 {target} 章，workspace/arc_*.json 仅找到 {len(entries)} 章"
        )
    return entries


def _immutable_fields(manifest: Dict[str, Any]) -> Tuple[str, ...]:
    return (
        "chapters",
        "model",
        "prompt_digest",
        "embedding_digest",
        "config_digest",
        "seed",
        "temperature",
    )


def _assert_immutable(existing: Dict[str, Any], requested: Dict[str, Any]) -> None:
    for key in _immutable_fields(requested):
        if existing.get(key) != requested.get(key):
            raise AcceptanceRunError(f"续跑参数不可变字段不一致：{key}")
    old_budget = float((existing.get("budget") or {}).get("max_cost_units") or 0)
    new_budget = float((requested.get("budget") or {}).get("max_cost_units") or 0)
    if old_budget != new_budget:
        raise AcceptanceRunError("续跑不能修改预算；请使用新的 --output 清单")


def _cost_snapshot(orch: Any, root: Path) -> Dict[str, float]:
    try:
        summary = orch.store.get_llm_cost_summary(project_id=str(root.name))
        return {
            "cost": float(summary.get("total_cost_cny") or 0),
            "tokens": int(summary.get("total_tokens") or 0),
        }
    except Exception:
        return {"cost": 0.0, "tokens": 0}


def _reconcile_cost(manifest: Dict[str, Any], observed: Dict[str, float]) -> None:
    """Reconcile persisted telemetry so a crash cannot hide already-paid work."""
    cost = manifest.setdefault("cost", {})
    baseline_cost = float(cost.get("baseline_cost") or 0)
    baseline_tokens = int(cost.get("baseline_tokens") or 0)
    observed_used = max(0.0, float(observed.get("cost") or 0) - baseline_cost)
    observed_tokens = max(0, int(observed.get("tokens") or 0) - baseline_tokens)
    cost["used"] = round(max(float(cost.get("used") or 0), observed_used), 6)
    cost["tokens"] = max(int(cost.get("tokens") or 0), observed_tokens)


def _quality_snapshot(root: Path, chapter_ids: Iterable[str], completed_count: int) -> Dict[str, Any]:
    """Read aggregate gate data only; never copy prose or full model output."""
    rows: List[Dict[str, Any]] = []
    for chapter_id in list(chapter_ids)[-10:]:
        reports = root / "workspace" / "chapters" / f"chapter_{chapter_id}" / "reports"
        gate_path = reports / "unified_gate.json"
        quality_path = reports / "quality.json"
        data: Dict[str, Any] = {}
        for candidate in (gate_path, quality_path):
            if not candidate.is_file():
                continue
            try:
                loaded = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(loaded, dict):
                data = loaded
                if candidate == gate_path:
                    break
        nested = data.get("quality") if isinstance(data.get("quality"), dict) else data
        blocked = nested.get("blocked_by") or (data.get("guard_summary") or {}).get("blocked_by") or []
        rows.append(
            {
                "chapter_id": str(chapter_id),
                "pass": bool(data.get("overall_pass", nested.get("overall_pass", False))),
                "score": nested.get("overall_score", data.get("overall_score")),
                "blocked_count": len(blocked) if isinstance(blocked, list) else 0,
                "report_present": bool(data),
            }
        )
    passed = [row for row in rows if row["report_present"]]
    return {
        "checkpoint_chapters": int(completed_count),
        "sampled_chapters": rows,
        "reported_pass_rate": round(sum(bool(row["pass"]) for row in passed) / len(passed), 4) if passed else None,
        "updated_at": _utc_now(),
    }


def _save_checkpoint(path: Path, manifest: Dict[str, Any]) -> None:
    manifest.setdefault("checkpoint", {})["completed_count"] = len(manifest.get("completed_chapters") or [])
    manifest["checkpoint"]["updated_at"] = _utc_now()
    _atomic_write_json(path, manifest)


def _ensure_runtime_shape(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade a plan-only manifest produced by an older runner in place."""
    defaults: Dict[str, Any] = {
        "interruptions": [],
        "retries": [],
        "manual_samples": [],
        "completed_chapters": [],
        "failed_chapters": [],
        "chapter_results": [],
        "quality_trend": [],
        "checkpoint": {"completed_count": 0, "last_chapter_id": "", "updated_at": None},
        "cost": {"used": 0.0, "tokens": 0, "currency": "local_units"},
    }
    for key, value in defaults.items():
        if key not in manifest:
            manifest[key] = value.copy() if isinstance(value, dict) else list(value)
    manifest["checkpoint"] = {**defaults["checkpoint"], **(manifest.get("checkpoint") or {})}
    manifest["cost"] = {**defaults["cost"], **(manifest.get("cost") or {})}
    return manifest


def execute_acceptance_run(
    args: argparse.Namespace,
    *,
    orchestrator_factory: Optional[Callable[[Any], Any]] = None,
    config_factory: Optional[Callable[[Path], Any]] = None,
) -> Dict[str, Any]:
    """Execute one manifest, with injectable factories for offline tests."""
    if not getattr(args, "start", False) or not getattr(args, "execute", False):
        raise AcceptanceRunError("真实执行必须同时提供 --start 和 --execute")
    if float(getattr(args, "budget", 0)) <= 0:
        raise AcceptanceRunError("真实执行必须提供正数 --budget")
    root = Path(getattr(args, "root", "") or "").resolve()
    entries = _preflight(root, int(args.chapters))
    output = Path(args.output)
    requested = build_manifest(args)

    if output.exists():
        if not bool(getattr(args, "resume", True)):
            raise AcceptanceRunError(f"清单已存在；续跑请使用 --resume，或改用新的 --output：{output}")
        existing_manifest = _ensure_runtime_shape(_load_json(output))
    else:
        existing_manifest = None

    from novel_agent.orchestrator import NovelOrchestrator
    from novel_agent.pipeline import PipelineConfig, assert_llm_ready
    from novel_agent.async_bridge import run_sync
    from novel_agent.control.long_run import chapter_run_is_failure

    config: Any = None
    try:
        config = config_factory(root) if config_factory else PipelineConfig.from_config(root)
        if config_factory is None:
            assert_llm_ready(root)
        requested = _bind_runtime_contract(args, config, root, requested)
        if existing_manifest is not None:
            _assert_immutable(existing_manifest, requested)
            manifest = existing_manifest
        else:
            manifest = requested
        manifest["launch_status"] = "explicit_acknowledged"
        manifest["operator_started"] = True
        manifest["status"] = "started"
        manifest["execution"] = {
            **(manifest.get("execution") or {}),
            "requested": True,
            "resume": bool(getattr(args, "resume", True)),
            "max_retries": max(0, int(getattr(args, "max_retries", 1))),
            "root_not_serialized": True,
        }
        _save_checkpoint(output, manifest)
        orch = orchestrator_factory(config) if orchestrator_factory else NovelOrchestrator(config)
    except Exception as exc:
        manifest = existing_manifest or requested
        manifest["status"] = "failed"
        manifest["error"] = _redact(exc)
        _save_checkpoint(output, manifest)
        return manifest
    observed_at_start = _cost_snapshot(orch, root)
    cost = manifest.setdefault("cost", {})
    if "baseline_cost" not in cost:
        cost["baseline_cost"] = observed_at_start["cost"]
        cost["baseline_tokens"] = observed_at_start["tokens"]
    _reconcile_cost(manifest, observed_at_start)
    _save_checkpoint(output, manifest)
    max_retries = max(0, int(getattr(args, "max_retries", 1)))
    completed = {str(item) for item in manifest.get("completed_chapters") or []}
    failed = {str(item) for item in manifest.get("failed_chapters") or []}
    try:
        for index, (arc_id, brief) in enumerate(entries):
            chapter_id = str(brief.get("chapter_id") or brief.get("id") or "").strip()
            if chapter_id in completed:
                continue
            if bool(getattr(args, "resume", True)) and orch._chapter_pipeline_complete(chapter_id):
                completed.add(chapter_id)
                manifest["completed_chapters"] = sorted(completed)
                manifest["chapter_results"].append({"chapter_id": chapter_id, "status": "recovered", "recovered_at": _utc_now()})
                _save_checkpoint(output, manifest)
                continue

            _reconcile_cost(manifest, _cost_snapshot(orch, root))
            used = float((manifest.get("cost") or {}).get("used") or 0)
            budget = float((manifest.get("budget") or {}).get("max_cost_units") or 0)
            if used >= budget:
                manifest["status"] = "paused"
                manifest["checkpoint"]["last_chapter_id"] = chapter_id
                manifest["error"] = "budget_exhausted_before_next_chapter"
                _save_checkpoint(output, manifest)
                return manifest

            attempts = 0
            success = False
            last_result: Any = None
            while attempts <= max_retries and not success:
                attempts += 1
                before = _cost_snapshot(orch, root)
                try:
                    orch.reset_round_token_accumulator()
                    result_pack = run_sync(
                        orch._run_chapter_briefs(
                            [brief], arc_id=arc_id, global_offset=index, all_chapters_ref=[item[1] for item in entries]
                        )
                    )
                    results = result_pack[0] if isinstance(result_pack, tuple) else result_pack
                    last_result = results[-1] if results else None
                    success = bool(last_result) and not chapter_run_is_failure(last_result)
                except Exception as exc:
                    last_result = exc
                    success = False
                after = _cost_snapshot(orch, root)
                round_cost = max(0.0, after["cost"] - before["cost"])
                round_tokens = max(0, after["tokens"] - before["tokens"])
                if round_tokens == 0:
                    try:
                        round_tokens = int(orch.consume_round_tokens() or 0)
                    except Exception:
                        round_tokens = 0
                manifest["cost"]["used"] = round((float(manifest["cost"].get("used") or 0) + round_cost), 6)
                manifest["cost"]["tokens"] = int(manifest["cost"].get("tokens") or 0) + round_tokens
                _reconcile_cost(manifest, after)
                if not success and attempts <= max_retries:
                    manifest["retries"].append({"chapter_id": chapter_id, "attempt": attempts, "reason": _redact(last_result)})
                if manifest["cost"]["used"] >= budget and not success:
                    break

            result_row = {
                "chapter_id": chapter_id,
                "status": "completed" if success else "failed",
                "attempts": attempts,
                "warning_count": len(getattr(last_result, "warnings", []) or []) if last_result else 0,
                "risk_level": _redact((getattr(last_result, "audit", {}) or {}).get("risk_level", "")) if last_result else "",
                "final_exists": bool((root / "workspace" / "chapters" / f"chapter_{chapter_id}" / "chapter_final.txt").is_file()),
                "updated_at": _utc_now(),
            }
            manifest["chapter_results"].append(result_row)
            if success:
                completed.add(chapter_id)
                failed.discard(chapter_id)
            else:
                failed.add(chapter_id)
            manifest["completed_chapters"] = sorted(completed)
            manifest["failed_chapters"] = sorted(failed)
            manifest["checkpoint"]["last_chapter_id"] = chapter_id
            if len(completed) % int(manifest.get("quality_check_interval") or 10) == 0 or len(completed) == int(args.chapters):
                manifest["quality_trend"].append(_quality_snapshot(root, sorted(completed), len(completed)))
                manifest["manual_samples"].append({"checkpoint_chapters": len(completed), "status": "pending_operator_review"})
            _save_checkpoint(output, manifest)
            if not success:
                manifest["status"] = "failed"
                manifest["error"] = "chapter_failed; see redacted chapter_results/retries"
                _save_checkpoint(output, manifest)
                return manifest
            if float(manifest["cost"]["used"]) >= budget and len(completed) < int(args.chapters):
                manifest["status"] = "paused"
                manifest["error"] = "budget_exhausted_after_chapter"
                _save_checkpoint(output, manifest)
                return manifest

        used = float((manifest.get("cost") or {}).get("used") or 0)
        budget = float((manifest.get("budget") or {}).get("max_cost_units") or 0)
        if used > budget:
            manifest["status"] = "failed"
            manifest["error"] = "budget_exceeded_after_chapter"
        else:
            manifest["status"] = "completed" if len(completed) >= int(args.chapters) else "paused"
        _save_checkpoint(output, manifest)
        return manifest
    except KeyboardInterrupt:
        manifest["status"] = "cancelled"
        manifest["interruptions"].append({"at": _utc_now(), "reason": "keyboard_interrupt"})
        _save_checkpoint(output, manifest)
        return manifest
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = _redact(exc)
        _save_checkpoint(output, manifest)
        return manifest
    finally:
        try:
            close = getattr(config, "close_llm_clients", None) if config is not None else None
            if close:
                run_sync(close())
        except Exception:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or execute an explicit long-form acceptance run")
    parser.add_argument("--chapters", type=int, choices=(20, 50, 100), default=20)
    parser.add_argument("--model", default=None)
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--prompt-digest", default="")
    parser.add_argument("--embedding", default=None)
    parser.add_argument("--embedding-digest", default="")
    parser.add_argument("--config", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--budget", type=float, default=0)
    parser.add_argument("--output", type=Path, default=Path("logs/longform-acceptance-manifest.json"))
    parser.add_argument("--root", type=Path, default=None, help="项目根目录（仅真实执行必需）")
    parser.add_argument("--start", action="store_true", help="确认允许真实运行")
    parser.add_argument("--execute", action="store_true", help="在 --start 后执行真实模型流水线")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True, help="从清单/章节检查点续跑")
    parser.add_argument("--max-retries", type=int, default=1, help="单章在 runner 层最多额外重试次数")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.execute:
        if not args.start:
            parser.error("--execute requires the separate explicit acknowledgement --start")
        if args.budget <= 0:
            parser.error("--execute requires a positive --budget")
        if args.root is None:
            parser.error("--execute requires --root <project>")
        try:
            manifest = execute_acceptance_run(args)
        except AcceptanceRunError as exc:
            manifest = build_manifest(args)
            manifest["status"] = "failed"
            manifest["error"] = _redact(exc)
            _atomic_write_json(args.output, manifest)
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
            return 2
    else:
        if args.start and args.budget <= 0:
            parser.error("--start requires a positive --budget")
        manifest = build_manifest(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("status") not in {"failed", "cancelled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
