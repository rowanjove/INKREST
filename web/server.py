"""Backward compatibility bridge for web.server.

All classes, functions, and state tracking variables have been modularized
into web/context.py, web/helpers.py, web/project_manager.py, web/preset_manager.py,
web/model_library.py, and web/app.py.

This module re-exports everything tests and legacy code may reference via
``import web.server as web_server``.  Assignments to ``web_server.BASE_DIR``
or ``web_server._active_project_id`` are intercepted and forwarded to
``web.context`` so that route handlers (which import ``web.context``) see the
updated values.
"""

import sys
import types
import logging

import web.context as _ctx
import web.helpers as _helpers
from web.app import app
from web.model_library import ModelLibrary
from web.project_manager import ProjectManager

# Force route modules to load so their functions are importable
from web.routes import chapters as _route_chapters  # noqa: F401
from web.routes import config as _route_config  # noqa: F401
from web.routes import database as _route_database  # noqa: F401
from web.routes import projects as _route_projects  # noqa: F401
from web.routes import prompts as _route_prompts  # noqa: F401
from web.routes import assets as _route_assets  # noqa: F401
from web.routes import assistant as _route_assistant  # noqa: F401
from web.routes import covers as _route_covers  # noqa: F401
from web.routes import outlines as _route_outlines  # noqa: F401
from web.routes import factory as _route_factory  # noqa: F401

# Models re-export
from web.models import (
    ProjectCreateRequest,
    NovelPlanRequest,
    ChapterPlanRequest,
    NovelRunRequest,
)

logger = logging.getLogger("web.server")

# ---- State variables (read from context) ----
# These are initial copies; __setattr__ on the module keeps them in sync.
BASE_DIR = _ctx.BASE_DIR
_active_project_id = _ctx._active_project_id
_task_manager = _ctx._task_manager
_project_lock = _ctx._project_lock

# ---- Context helpers ----
get_root_dir = _ctx.get_root_dir
require_project_root = _ctx.require_project_root
activate_project = _ctx.activate_project
reset_plugin_manager = _ctx.reset_plugin_manager
_get_task_manager = _ctx._get_task_manager
get_project_store = _ctx.get_project_store
_has_active_tasks = _ctx._has_active_tasks
_ensure_no_active_tasks = _ctx._ensure_no_active_tasks

# ---- Helpers re-export ----
_validate_id = _helpers._validate_id
_ensure_dirs = _helpers._ensure_dirs
_init_prompt_defaults = _helpers._init_prompt_defaults
_sync_outline_to_character_cards = _helpers._sync_outline_to_character_cards
_sync_outline_to_world_bible = _helpers._sync_outline_to_world_bible
_preserve_outline_identity = _helpers._preserve_outline_identity
get_outline = _helpers.get_outline

_read_json = _helpers._read_json
_read_text = _helpers._read_text
_read_yaml = _helpers._read_yaml
_write_yaml = _helpers._write_yaml
SECRET_MASK = _helpers.SECRET_MASK
SECRET_KEYS = _helpers.SECRET_KEYS
_mask_config_secrets = _helpers._mask_config_secrets
_merge_preserving_masked_secrets = _helpers._merge_preserving_masked_secrets
_custom_assets_dir = _helpers._custom_assets_dir
_asset_label_path = _helpers._asset_label_path
_load_asset_labels = _helpers._load_asset_labels
_save_asset_label = _helpers._save_asset_label
_custom_asset_rel_path = _helpers._custom_asset_rel_path
_resolve_asset_file = _helpers._resolve_asset_file
_delete_chapter_dir = _helpers._delete_chapter_dir
PROMPT_ROLES = _helpers.PROMPT_ROLES
ASSET_FILES = _helpers.ASSET_FILES
CONFIG_ASSET_FILES = _helpers.CONFIG_ASSET_FILES
_ALL_ASSET_FILES = _helpers._ALL_ASSET_FILES

# ---- Route functions re-export (for tests that call web_server.xxx()) ----
rewrite_chapter = _route_chapters.rewrite_chapter
resume_chapter_audit = _route_chapters.resume_chapter_audit
get_chapter = _route_chapters.get_chapter
list_chapters = _route_chapters.list_chapters
suggest_chapter_goal = _route_chapters.suggest_chapter_goal
clear_database = _route_database.clear_database
get_scale_profile = _route_database.get_scale_profile
get_config = _route_config.get_config
create_project = _route_projects.create_project
switch_project = _route_projects.switch_project
update_outline = _route_outlines.update_outline
plan_novel = _route_outlines.plan_novel
generate_chapter_plan = _route_outlines.generate_chapter_plan


# ---- Intercept attribute assignments to sync state to web.context ----
# Sync any attribute that exists in web.context so test patches propagate.
_ALWAYS_SYNC = frozenset({
    "BASE_DIR", "_active_project_id", "_task_manager",
    "project_manager", "preset_manager",
})

_this_module = sys.modules[__name__]
_original_dict = _this_module.__dict__


class _ServerShim(types.ModuleType):
    """Thin module wrapper that intercepts __setattr__ for state variables."""

    def __setattr__(self, name: str, value):
        _original_dict[name] = value
        # Sync to web.context if it's a known state var or exists in context
        if name in _ALWAYS_SYNC or hasattr(_ctx, name):
            setattr(_ctx, name, value)

    def __getattr__(self, name: str):
        try:
            return _original_dict[name]
        except KeyError:
            # Delegate to context for lazily-loaded attrs like project_manager
            return getattr(_ctx, name)


# Replace the module in sys.modules with the shim
_shim = _ServerShim(__name__)
_shim.__dict__.update(_original_dict)
_shim.__file__ = __file__
_shim.__package__ = __package__
_shim.__path__ = getattr(_this_module, "__path__", None)
_shim.__spec__ = getattr(_this_module, "__spec__", None)
sys.modules[__name__] = _shim
