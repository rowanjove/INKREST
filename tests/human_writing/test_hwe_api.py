"""API integration tests for HWE endpoints."""

from fastapi.testclient import TestClient
from web.app import app

client = TestClient(app)


def test_api_list_rules():
    response = client.get("/api/hwe/rules")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] >= 20
    assert "rules" in data
    assert len(data["rules"]) == data["count"]
    assert "ruleset_version" in data


def test_api_scan_text():
    sample_text = "这不是普通的匕首，而是一柄被诅咒的凶器。林默喉结滚动，倒吸一口凉气。"
    response = client.post(
        "/api/hwe/scan",
        json={"text": sample_text, "mode": "assist"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["char_count"] == len(sample_text)
    assert "scores" in data
    assert "issues" in data
    assert len(data["issues"]) >= 1

    issue = data["issues"][0]
    assert "hwe" in issue
    assert "start" in issue["hwe"]
    assert "end" in issue["hwe"]
    assert "line" in issue["hwe"]
    assert "paragraph" in issue["hwe"]
    assert "matched_text" in issue["hwe"]


def test_api_patch_plan_and_generate():
    sample_text = (
        "傍晚时分，天色渐暗。\n\n"
        "这不是普通的匕首，而是一柄被诅咒的凶器。"
        "林默紧攥着拳头。显然他非常害怕，内心的恐慌无法抑制。\n\n"
        "他深吸了一口气。"
    )
    # 1. Plan patches
    plan_res = client.post(
        "/api/hwe/patch/plan",
        json={"text": sample_text, "project_characters": ["林默"]},
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert isinstance(plan_data, list)
    assert len(plan_data) >= 1

    first_patch = plan_data[0]
    assert "patch_id" in first_patch
    assert "original_text" in first_patch
    assert "protected_spans" in first_patch

    # 2. Generate patch candidate
    gen_res = client.post(
        "/api/hwe/patch/generate",
        json={"patch": first_patch},
    )
    assert gen_res.status_code == 200
    candidate_data = gen_res.json()
    assert "patch_id" in candidate_data
    assert "candidate_text" in candidate_data
    assert "fidelity" in candidate_data
    assert candidate_data["fidelity"]["passed"] is True
    assert "diff_unified" in candidate_data


def test_api_prompt_preview():
    response = client.post(
        "/api/hwe/prompt-preview",
        json={
            "scene_type": "高压对峙",
            "pov": "第三人称限知",
            "characters": ["林默"],
            "user_constraints": ["严禁任何网络梗"],
            "max_budget": 1000,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "prompt_block" in data
    assert "[本章文风与去套路约束]" in data["prompt_block"]
    assert "【用户要求】严禁任何网络梗" in data["prompt_block"]
    assert data["within_budget"] is True
    assert data["char_count"] <= 1000


def test_api_semantic_review():
    sample_text = (
        "他深吸了一口气，他意识到自己其实正在害怕。\n"
        "殊不知，命运的齿轮已经悄然转动。\n"
    )
    response = client.post(
        "/api/hwe/semantic-review",
        json={
            "text": sample_text,
            "pov": "第三人称限知",
            "template_risk": 40.0,
            "user_requested": True,
        },
    )
    assert response.status_code == 200
    issues = response.json()
    assert isinstance(issues, list)
    assert len(issues) >= 1
    assert issues[0]["hwe"]["source"] == "semantic_model"


def test_api_eval_run_and_latest():
    res = client.post("/api/hwe/eval/run")
    assert res.status_code == 200
    report = res.json()
    assert report["benchmark_name"] == "HWE 1.0 Benchmark Suite"
    assert report["metrics"]["total_cases"] >= 7
    assert report["fpr_target_met"] is True

    latest_res = client.get("/api/hwe/eval/latest")
    assert latest_res.status_code == 200
    latest_data = latest_res.json()
    assert latest_data is not None
    assert latest_data["metrics"]["total_cases"] >= 7


def test_api_preferences_and_resolve():
    pref_res = client.get("/api/hwe/preferences")
    assert pref_res.status_code == 200
    pref_data = pref_res.json()
    assert "suppressed_rules" in pref_data
    assert "rule_weights" in pref_data

    update_res = client.post(
        "/api/hwe/preferences",
        json={"suppress_rule": "HWE.RHYTHM.STACCATO_ABUSE", "reason": "Test suppression"},
    )
    assert update_res.status_code == 200
    updated_pref = update_res.json()
    assert "HWE.RHYTHM.STACCATO_ABUSE" in updated_pref["suppressed_rules"]

    resolve_res = client.post(
        "/api/hwe/issues/issue_test_01/resolve",
        json={"action": "false_positive", "rule_id": "HWE.STAGING.BINARY_CONTRAST"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "ok"


