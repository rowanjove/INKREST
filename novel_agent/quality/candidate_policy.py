"""Deterministic report-only policy for deciding when candidates are valuable.

The policy is intentionally a *recommendation* layer.  It never calls a model,
creates a candidate, or changes the single-candidate default.  Callers may show
the returned reasons in the UI and require an explicit user action before
running an expensive candidate workflow.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


POLICY_SCHEMA_VERSION = 1
DEFAULT_MODE = "manual_only"
VALID_MODES = {"manual_only", "report_only", "explicit_candidates_only", "auto"}


@dataclass(frozen=True)
class CandidatePolicyConfig:
    mode: str = DEFAULT_MODE
    chapter_cost_budget: int = 3
    volume_cost_budget: int = 12
    max_concurrency: int = 1
    minimum_risk_score: float = 0.55

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None = None) -> "CandidatePolicyConfig":
        raw = value or {}
        mode = str(raw.get("mode") or DEFAULT_MODE).strip().lower()
        if mode not in VALID_MODES:
            mode = DEFAULT_MODE
        try:
            chapter_budget = max(1, min(int(raw.get("chapter_cost_budget", raw.get("cost_budget", 3))), 100))
        except (TypeError, ValueError):
            chapter_budget = 3
        try:
            volume_budget = max(chapter_budget, min(int(raw.get("volume_cost_budget", 12)), 1000))
        except (TypeError, ValueError):
            volume_budget = max(chapter_budget, 12)
        try:
            concurrency = max(1, min(int(raw.get("max_concurrency", 1)), 8))
        except (TypeError, ValueError):
            concurrency = 1
        try:
            risk = max(0.0, min(float(raw.get("minimum_risk_score", 0.55)), 1.0))
        except (TypeError, ValueError):
            risk = 0.55
        return cls(mode, chapter_budget, volume_budget, concurrency, risk)

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": POLICY_SCHEMA_VERSION, **asdict(self)}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _truthy(value: Any) -> bool:
    return bool(value) and str(value).strip().lower() not in {"0", "false", "no", "none"}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_candidate_policy(
    chapter_id: str,
    *,
    chapter_index: int | None = None,
    volume_position: int | None = None,
    volume_size: int | None = None,
    scene_kind: str = "",
    scene_tags: Sequence[str] = (),
    quality_report: Mapping[str, Any] | None = None,
    voice_lab: Mapping[str, Any] | None = None,
    recent_metrics: Mapping[str, Any] | None = None,
    explicit_mark: bool = False,
    config: CandidatePolicyConfig | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stable recommendation and evidence for one chapter.

    The result is safe to persist in a report.  ``recommend`` means that a
    human-facing UI should offer a candidate review; ``generate`` is always
    false unless a caller explicitly opts into the experimental ``auto`` mode
    *and* the scene is explicitly marked.  The default remains manual-only.
    """

    policy = config if isinstance(config, CandidatePolicyConfig) else CandidatePolicyConfig.from_mapping(config)
    quality = _mapping(quality_report)
    voice = _mapping(voice_lab)
    metrics = _mapping(recent_metrics)
    tags = {str(item).strip().lower() for item in scene_tags if str(item).strip()}
    kind = str(scene_kind or "").strip().lower()
    reasons: list[dict[str, Any]] = []

    def add(code: str, evidence: Any = None, *, weight: float = 1.0) -> None:
        item: dict[str, Any] = {"code": code, "weight": round(float(weight), 4)}
        if evidence not in (None, "", [], {}):
            item["evidence"] = evidence
        reasons.append(item)

    pos = volume_position if volume_position is not None else chapter_index
    if pos is not None and int(pos) == 1:
        add("volume_start", pos)
    if pos is not None and volume_size and int(pos) == int(volume_size):
        add("volume_end", {"position": pos, "size": volume_size})
    high_value_terms = {"climax", "高潮", "reveal", "揭密", "揭示", "key_decision", "关键决定", "关键决策", "turning_point", "转折"}
    if kind in high_value_terms or tags.intersection(high_value_terms):
        add("high_value_scene", kind or sorted(tags.intersection(high_value_terms)))
    layers = _mapping(quality.get("quality_layers"))
    l0 = _mapping(layers.get("L0"))
    if _truthy(quality.get("l0_pass")) or str(l0.get("status") or "").lower() == "pass":
        l1 = _mapping(layers.get("L1"))
        risk = max(_number(quality.get("l1_risk")), _number(l1.get("risk_score")), _number(l1.get("risk")))
        if risk >= policy.minimum_risk_score or str(l1.get("status") or "").lower() in {"review", "warning", "error"}:
            add("l0_pass_l1_risk", {"risk_score": risk, "l1_status": l1.get("status")}, weight=1.2)
    drift = max(_number(voice.get("drift_score")), _number(voice.get("recent_drift")), _number(metrics.get("voice_drift")))
    if drift >= policy.minimum_risk_score or _truthy(voice.get("drift_warning")):
        add("voice_drift", {"drift_score": drift}, weight=1.1)
    rewrite_rate = max(_number(metrics.get("rewrite_rate")), _number(metrics.get("recent_rework_rate")))
    rewrite_rounds = max(_number(metrics.get("rewrite_rounds")), _number(quality.get("rewrite_rounds")))
    if rewrite_rate >= 0.35 or rewrite_rounds >= 2:
        add("rewrite_rise", {"rewrite_rate": rewrite_rate, "rewrite_rounds": rewrite_rounds}, weight=1.0)
    if explicit_mark:
        add("explicit_mark", True, weight=2.0)

    score = min(1.0, sum(float(item["weight"]) for item in reasons) / 3.0)
    recommended = bool(reasons)
    # Auto mode is deliberately double opt-in and still constrained by an
    # explicit mark; report-only/manual-only never launch generation.
    generate = policy.mode == "auto" and explicit_mark and recommended
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "chapter_id": str(chapter_id),
        "mode": policy.mode,
        "recommend": recommended,
        "generate": generate,
        "report_only": policy.mode in {"manual_only", "report_only"},
        "score": round(score, 4),
        "reasons": reasons,
        "reason_codes": [str(item["code"]) for item in reasons],
        "budget": {
            "chapter_cost_units": policy.chapter_cost_budget,
            "volume_cost_units": policy.volume_cost_budget,
            "max_concurrency": policy.max_concurrency,
        },
        "policy": policy.to_dict(),
    }


def should_offer_candidates(*args: Any, **kwargs: Any) -> bool:
    """Compatibility helper used by UI and adapters."""

    return bool(evaluate_candidate_policy(*args, **kwargs).get("recommend"))


build_candidate_policy = evaluate_candidate_policy


__all__ = [
    "CandidatePolicyConfig",
    "DEFAULT_MODE",
    "POLICY_SCHEMA_VERSION",
    "build_candidate_policy",
    "evaluate_candidate_policy",
    "should_offer_candidates",
]
