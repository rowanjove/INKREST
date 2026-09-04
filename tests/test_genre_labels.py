from pathlib import Path

from web.genre_labels import normalize_genre_label


def test_internal_theme_id_uses_display_name(tmp_path: Path):
    assert normalize_genre_label(tmp_path, "dushi") == "都市"
    assert normalize_genre_label(tmp_path, "lishi") == "历史"


def test_free_form_genre_is_preserved(tmp_path: Path):
    assert normalize_genre_label(tmp_path, "都市异能") == "都市异能"
