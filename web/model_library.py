"""Model library manager for configured LLM endpoints."""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List
import yaml
from fastapi import HTTPException

from web.helpers import SECRET_MASK, SECRET_KEYS, _write_yaml
from novel_agent.pipeline import resolve_global_config_dir, load_global_pipeline_file, write_pipeline_file


SLOT_EMPTY = ""
SLOT_DAILY = "daily"
SLOT_REASONING = "reasoning"
SLOT_BACKUP = "backup"
VALID_SLOTS = frozenset({SLOT_EMPTY, SLOT_DAILY, SLOT_REASONING, SLOT_BACKUP})


def _default_slots() -> Dict[str, Any]:
    return {"daily": "", "reasoning": "", "backup": []}


class ModelLibrary:
    """Manages global LLM model library (models.json) and tier slots."""

    DEFAULT_MODELS = {
        "deepseek-v4-flash": {
            "name": "DeepSeek V4 Flash",
            "provider": "openai",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-v4-flash",
            "max_tokens": 8192,
            "temperature": 0.7,
            "timeout": 120,
            "proxy": "",
        },
        "deepseek-v4-pro": {
            "name": "DeepSeek V4 Pro",
            "provider": "openai",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-v4-pro",
            "max_tokens": 8192,
            "temperature": 0.6,
            "timeout": 180,
            "proxy": "",
        },
    }

    LEGACY_PRESET_IDS = {
        "deepseek-v3",
        "deepseek-r1",
        "deepseek-chat",
        "deepseek-reasoner",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-4-sonnet",
        "claude-sonnet-4",
        "claude-opus-4-1",
        "gemini-2-5-pro",
        "gemini-2-5-flash",
        "gemini-3-flash",
        "qwen3-235b",
        "qwen-max",
        "ollama-local",
        "custom",
    }

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        grandparent = Path(root_dir).parent.parent
        if (grandparent / "projects.json").exists():
            global_config = grandparent / "config"
        else:
            global_config = Path(root_dir) / "config"
        self.config_path = global_config / "models.json"

    def _load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            data = {
                "models": copy.deepcopy(self.DEFAULT_MODELS),
                "defaults_seeded": True,
                "slots": _default_slots(),
                "slots_version": 0,
            }
            self._migrate_slots_from_pipeline(data)
            self._save(data)
            self._sync_slots_to_pipeline(data["slots"])
            return data
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                500,
                f"models.json 格式错误：{exc}。请在设置中修复模型库配置。",
            ) from exc
        except OSError as exc:
            raise HTTPException(500, f"无法读取 models.json：{exc}") from exc
        if not isinstance(data, dict):
            raise HTTPException(500, "models.json 根节点必须是 JSON 对象。")
        data.setdefault("slots", _default_slots())
        models = data.setdefault("models", {})
        changed = False
        for model_id, default in self.DEFAULT_MODELS.items():
            if model_id not in models:
                models[model_id] = copy.deepcopy(default)
                changed = True
        if not data.get("defaults_seeded"):
            data["defaults_seeded"] = True
            changed = True
        if self._migrate_slots_from_pipeline(data):
            changed = True
        if changed:
            self._save(data)
        return data

    def _migrate_slots_from_pipeline(self, data: Dict[str, Any]) -> bool:
        if int(data.get("slots_version") or 0) >= 1:
            return False
        slots = data.setdefault("slots", _default_slots())
        global_dir = resolve_global_config_dir(self.root_dir)
        if global_dir:
            llm = load_global_pipeline_file(global_dir).get("llm") or {}
        else:
            path = self.root_dir / "config" / "pipeline.yaml"
            llm = (
                yaml.safe_load(path.read_text(encoding="utf-8")).get("llm", {})
                if path.is_file()
                else {}
            )
        if isinstance(llm, dict):
            daily = str(llm.get("daily_model_id") or llm.get("default_model_id") or "").strip()
            if daily and not slots.get("daily"):
                slots["daily"] = daily
            reasoning = str(llm.get("reasoning_model_id") or "").strip()
            if reasoning and not slots.get("reasoning"):
                slots["reasoning"] = reasoning
            backup = llm.get("fallback_model_ids") or []
            if isinstance(backup, list) and backup and not slots.get("backup"):
                slots["backup"] = [str(x) for x in backup if x]
        data["slots_version"] = 1
        return True

    def _slot_for_model(self, slots: Dict[str, Any], model_id: str) -> str:
        if slots.get("daily") == model_id:
            return SLOT_DAILY
        if slots.get("reasoning") == model_id:
            return SLOT_REASONING
        backup = slots.get("backup") or []
        if model_id in backup:
            return SLOT_BACKUP
        return SLOT_EMPTY

    def _remove_model_from_slots(self, slots: Dict[str, Any], model_id: str) -> None:
        if slots.get("daily") == model_id:
            slots["daily"] = ""
        if slots.get("reasoning") == model_id:
            slots["reasoning"] = ""
        backup = slots.get("backup") or []
        if model_id in backup:
            slots["backup"] = [x for x in backup if x != model_id]

    def _sync_slots_to_pipeline(self, slots: Dict[str, Any]) -> None:
        daily = str(slots.get("daily") or "").strip()
        reasoning = str(slots.get("reasoning") or "").strip()
        backup = [str(x) for x in (slots.get("backup") or []) if x]
        llm_patch: Dict[str, Any] = {}
        if daily:
            llm_patch["daily_model_id"] = daily
            llm_patch["default_model_id"] = daily
        if reasoning:
            llm_patch["reasoning_model_id"] = reasoning
        elif daily:
            llm_patch["reasoning_model_id"] = daily
        if backup:
            llm_patch["fallback_model_ids"] = backup

        def _apply_llm_patch(on_disk: Dict[str, Any]) -> None:
            llm = {**(on_disk.get("llm") or {}), **llm_patch}
            if not daily:
                llm.pop("daily_model_id", None)
                llm.pop("default_model_id", None)
            if not reasoning:
                if daily:
                    llm["reasoning_model_id"] = daily
                else:
                    llm.pop("reasoning_model_id", None)
            if not backup:
                llm.pop("fallback_model_ids", None)
            on_disk["llm"] = llm

        global_dir = resolve_global_config_dir(self.root_dir)
        if global_dir:
            path = global_dir / "pipeline.yaml"
            on_disk = load_global_pipeline_file(global_dir)
            _apply_llm_patch(on_disk)
            write_pipeline_file(path, on_disk)
            return
        path = self.root_dir / "config" / "pipeline.yaml"
        if path.is_file():
            on_disk = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            on_disk = {}
        _apply_llm_patch(on_disk)
        write_pipeline_file(path, on_disk)

    def get_slots(self) -> Dict[str, Any]:
        data = self._load()
        slots = data.get("slots") or _default_slots()
        return {
            "daily": slots.get("daily") or "",
            "reasoning": slots.get("reasoning") or "",
            "backup": list(slots.get("backup") or []),
        }

    def set_model_slot(self, model_id: str, slot: str) -> Dict[str, Any]:
        slot = (slot or "").strip().lower()
        if slot not in VALID_SLOTS:
            raise HTTPException(400, f"无效档位，可选：空、daily、reasoning、backup")
        data = self._load()
        models = data.get("models", {})
        if model_id not in models:
            raise HTTPException(404, f"Model {model_id} not found")
        if models[model_id].get("type") == "image" and slot:
            raise HTTPException(400, "图像模型不能设置文字档位")
        slots = data.setdefault("slots", _default_slots())
        self._remove_model_from_slots(slots, model_id)
        if slot == SLOT_DAILY:
            slots["daily"] = model_id
        elif slot == SLOT_REASONING:
            slots["reasoning"] = model_id
        elif slot == SLOT_BACKUP:
            backup = list(slots.get("backup") or [])
            if model_id not in backup:
                backup.append(model_id)
            slots["backup"] = backup
        data["slots"] = slots
        self._save(data)
        self._sync_slots_to_pipeline(slots)
        entry = {**models[model_id], "id": model_id, "slot": self._slot_for_model(slots, model_id)}
        entry["has_api_key"] = bool(entry.get("api_key"))
        entry["api_key"] = ""
        return entry

    def _save(self, data: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_models(self) -> List[Dict[str, Any]]:
        data = self._load()
        models = data.get("models", {})
        slots = data.get("slots") or _default_slots()
        result = []
        from novel_agent.pricing import pricing_hint_for_model

        for mid, m in models.items():
            entry = {**m, "id": mid}
            entry["slot"] = self._slot_for_model(slots, mid)
            entry["has_api_key"] = bool(entry.get("api_key"))
            entry["api_key"] = ""
            entry.update(pricing_hint_for_model(mid, m))
            result.append(entry)
        return result

    def get_model(self, model_id: str) -> Dict[str, Any]:
        data = self._load()
        models = data.get("models", {})
        if model_id not in models:
            raise HTTPException(404, f"Model {model_id} not found")
        return {"id": model_id, **models[model_id]}

    def save_model(self, model_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        data = self._load()
        if "models" not in data:
            data["models"] = {}
        existing = data["models"].get(model_id, {})
        entry = {k: v for k, v in config.items() if k != "id"}
        if entry.get("api_key") in ("", SECRET_MASK, "***", "******"):
            if existing.get("api_key"):
                entry["api_key"] = existing["api_key"]
            else:
                entry.pop("api_key", None)
        data["models"][model_id] = entry
        self._save(data)
        saved = {"id": model_id, **entry}
        saved["has_api_key"] = bool(saved.get("api_key"))
        saved["api_key"] = ""
        return saved

    def delete_model(self, model_id: str) -> None:
        data = self._load()
        models = data.get("models", {})
        if model_id not in models:
            raise HTTPException(404, f"Model {model_id} not found")
        del models[model_id]
        slots = data.setdefault("slots", _default_slots())
        self._remove_model_from_slots(slots, model_id)
        data["slots"] = slots
        self._save(data)
        self._sync_slots_to_pipeline(slots)
        global_dir = resolve_global_config_dir(self.root_dir)
        if global_dir:
            config_path = global_dir / "pipeline.yaml"
            config = load_global_pipeline_file(global_dir)
        else:
            config_path = self.root_dir / "config" / "pipeline.yaml"
            if not config_path.exists():
                return
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        llm = config.get("llm", {})
        if isinstance(llm, dict):
            if llm.get("assistant", {}).get("model_ref") == model_id:
                llm.pop("assistant", None)
            overrides = llm.get("overrides", {})
            if isinstance(overrides, dict):
                for role in list(overrides):
                    if overrides.get(role, {}).get("model_ref") == model_id:
                        overrides.pop(role, None)
            write_pipeline_file(config_path, config)

    def test_model(self, config: Dict[str, Any], test_context_tokens: int = None) -> Dict[str, Any]:
        from novel_agent.agents.base import OpenAILLM

        model_id = config.get("model_id")
        if model_id:
            stored = self.get_model(model_id)
            cfg = {k: v for k, v in stored.items() if k != "id"}
        else:
            cfg = config

        if cfg.get("type") == "image":
            import httpx
            url = f"{cfg.get('base_url', 'https://api.openai.com/v1').rstrip('/')}/images/generations"
            headers = {
                "Authorization": f"Bearer {cfg.get('api_key', '')}",
                "Content-Type": "application/json"
            }
            body = {
                "model": cfg.get("model", "dall-e-3"),
                "prompt": "test",
                "n": 1
            }
            try:
                with httpx.Client(proxy=cfg.get("proxy") or None, timeout=float(cfg.get("timeout", 30))) as client:
                    resp = client.post(url, headers=headers, json=body)
                    if resp.status_code == 200:
                        res_data = resp.json()
                        if "data" in res_data and len(res_data["data"]) > 0:
                            return {"success": True, "message": "图像生成接口测试成功！已成功握手。"}
                    try:
                        err_msg = resp.json().get("error", {}).get("message", resp.text)
                    except Exception:
                        err_msg = resp.text
                    return {"success": False, "error": f"HTTP {resp.status_code}: {err_msg}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        llm = OpenAILLM(
            base_url=cfg.get("base_url", "https://api.openai.com/v1"),
            api_key=cfg.get("api_key", ""),
            model=cfg.get("model", "gpt-4o-mini"),
            max_tokens=cfg.get("max_tokens", 4096),
            temperature=cfg.get("temperature", 0.7),
            timeout=float(cfg.get("timeout", 30)),
            max_retries=1,
            proxy=cfg.get("proxy", ""),
        )
        try:
            if test_context_tokens:
                return llm.test_context_budget(test_context_tokens)
            return llm.test()
        finally:
            llm.close()
