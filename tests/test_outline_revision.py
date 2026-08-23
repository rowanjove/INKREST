from __future__ import annotations

from web.routes.outlines import _load_outline_revision, _outline_digest, _save_outline_revision


def test_outline_revision_is_append_only_and_digest_bound(tmp_path):
    first = {"core_theme": "旧主题", "macro_outline": [{"arc_id": "A01"}]}
    state0 = _load_outline_revision(tmp_path, {})
    rev1 = _save_outline_revision(tmp_path, first, previous={**state0, "outline": {}})
    second = {"core_theme": "新主题", "macro_outline": [{"arc_id": "A01"}]}
    rev2 = _save_outline_revision(tmp_path, second, previous={**rev1, "outline": first})
    assert rev1["revision"] == 1
    assert rev2["revision"] == 2
    assert rev2["digest"] == _outline_digest(second)
    assert (tmp_path / "workspace" / "outline_history" / "v1.json").is_file()
    assert _load_outline_revision(tmp_path, second)["digest"] == rev2["digest"]
