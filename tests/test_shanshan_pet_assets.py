import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PET_ROOT = ROOT / "web" / "frontend" / "src" / "assets" / "pet" / "shanshan"
PET_SPRITE = ROOT / "web" / "frontend" / "src" / "components" / "pet" / "PetSprite.vue"
PET_STORE = ROOT / "web" / "frontend" / "src" / "stores" / "pet.ts"
PET_BUBBLE = ROOT / "web" / "frontend" / "src" / "views" / "PetBubbleView.vue"


def test_shanshan_special_state_assets_are_square_and_distinct() -> None:
    names = [
        "working.png",
        "dragging.png",
        "question.png",
        "hide_left.png",
        "hide_right.png",
        "hide_top.png",
        "hide_bottom.png",
    ]
    contents = []
    for name in names:
        path = PET_ROOT / "static" / name
        with Image.open(path) as image:
            assert image.size == (256, 256)
        contents.append(path.read_bytes())

    assert len(set(contents)) == len(contents)


def test_shanshan_question_marks_keep_left_side_dots() -> None:
    with Image.open(PET_ROOT / "static" / "question.png") as image:
        alpha = image.convert("RGBA").getchannel("A")

    upper_left_dot = alpha.crop((31, 58, 56, 64))
    middle_left_dot = alpha.crop((33, 98, 47, 104))

    assert sum(value > 10 for value in upper_left_dot.getdata()) >= 40
    assert sum(value > 10 for value in middle_left_dot.getdata()) >= 40


def test_shanshan_sprite_uses_directional_assets_and_status_badges() -> None:
    source = PET_SPRITE.read_text(encoding="utf-8")

    assert "props.state === 'hide-left') return { file: hideLeftPng" in source
    assert "props.state === 'hide-right') return { file: hideRightPng" in source
    assert "props.state === 'hide-top') return { file: hideTopPng" in source
    assert "props.state === 'hide-bottom') return { file: hideBottomPng" in source
    assert "props.state === 'working') return { file: workingSheet" in source
    assert "props.state === 'error') return { file: errorSheet" in source
    assert "badge: successBadge" in source
    assert "badge: errorBadge" in source


def test_shanshan_metadata_uses_readable_name_and_complete_states() -> None:
    metadata = json.loads((PET_ROOT / "pet.json").read_text(encoding="utf-8"))

    assert metadata["name"] == "山山"
    assert set(metadata["states"]) == {
        "idle",
        "working",
        "success",
        "error",
        "offline",
        "dragging",
        "question",
        "hide-left",
        "hide-right",
        "hide-top",
        "hide-bottom",
    }


def test_ignored_failed_tasks_sync_across_pet_windows() -> None:
    source = PET_STORE.read_text(encoding="utf-8")

    assert "window.addEventListener('storage', syncIgnoredFailedTasks)" in source
    assert "window.removeEventListener('storage', syncIgnoredFailedTasks)" in source
    assert "ignoredFailedTaskIds.value = readIgnoredFailedTaskIds()" in source


def test_shanshan_pet_uses_transient_success_and_step_labels() -> None:
    source = PET_STORE.read_text(encoding="utf-8")
    assert "flashTransientState" in source
    assert "formatTaskStep" in source
    assert "pending_total" in source


def test_shanshan_pipeline_state_maps_working_and_question() -> None:
    pet_state = ROOT / "web" / "frontend" / "src" / "utils" / "petState.ts"
    source = pet_state.read_text(encoding="utf-8")
    store_source = PET_STORE.read_text(encoding="utf-8")

    assert "hasPipelineProblem" in source
    assert "isPipelineRunning" in source
    assert "mapContextToPetState" in source
    assert "return 'working'" in source
    assert "return 'question'" in source
    assert "mapContextToPetState" in store_source
    assert "bubblePulseState" in store_source
    assert "疑惑" in store_source


def test_pet_bubble_pulse_uses_effective_state_not_hide_sprite() -> None:
    bubble = PET_BUBBLE.read_text(encoding="utf-8")
    assert "pet.bubblePulseState" in bubble
    assert ':class="pet.state"' not in bubble.split("status-pulse-mini")[1].split(">")[0]


def test_pet_view_edge_auto_hide_hooks() -> None:
    pet_view = ROOT / "web" / "frontend" / "src" / "views" / "PetView.vue"
    pet_window = ROOT / "web" / "frontend" / "src" / "composables" / "usePetWindowInteraction.ts"
    edge_dock = ROOT / "web" / "frontend" / "src" / "composables" / "usePetEdgeDock.ts"
    shell_source = pet_view.read_text(encoding="utf-8")
    window_source = pet_window.read_text(encoding="utf-8")
    dock_source = edge_dock.read_text(encoding="utf-8")

    assert "usePetWindowInteraction" in shell_source
    assert "usePetEdgeDock" in window_source
    assert "applyEdgeDockIfNeeded" in window_source
    assert "restoreFromEdge" in window_source
    assert "setHiddenAtEdge" in dock_source or "setHiddenAtEdge" in PET_STORE.read_text(encoding="utf-8")


def test_pet_bubble_refresh_indicator_does_not_shift_layout() -> None:
    source = PET_BUBBLE.read_text(encoding="utf-8")

    assert 'class="sync-text-mini" :class="{ visible: pet.loading }"' in source
    assert ".shell-footer-compact {\n  min-height: 14px;" in source
    assert ".sync-text-mini.visible {" in source
