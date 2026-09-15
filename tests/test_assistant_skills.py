from novel_agent.assistant.skills.registry import get_skill_registry


def test_skill_registry_loads_builtins():
    registry = get_skill_registry()
    skills = registry.list_skills()
    assert len(skills) >= 15

    expected_commands = [
        "/续写", "/润色", "/扩写", "/压缩", "/对白", "/人物口吻",
        "/伏笔", "/查设定", "/查冲突", "/审章", "/策划", "/拆场",
        "/章纲", "/总结", "/诊断"
    ]
    commands = [s.command for s in skills]
    for exp in expected_commands:
        assert exp in commands, f"Missing skill command: {exp}"

    # Test retrieving skills
    polish = registry.get("polish")
    assert polish is not None
    assert polish.command == "/润色"
    assert polish.produces_patch is True

    review = registry.get("review_chapter")
    assert review is not None
    assert review.command == "/审章"
    assert review.produces_patch is False

    foreshadowing = registry.get("foreshadowing")
    assert foreshadowing is not None
    assert foreshadowing.command == "/伏笔"

    # Test slash command detection
    detected = registry.find_by_command("/续写 接下来江炘跳上了飞行器")
    assert detected is not None
    assert detected.id == "continue"


def test_intent_router():
    from novel_agent.assistant.router import IntentRouter

    assert IntentRouter.detect_skill("帮我润色一下这句话") == "polish"
    assert IntentRouter.detect_skill("这章适合埋下什么伏笔？") == "foreshadowing"
    assert IntentRouter.detect_skill("检查一下这章有没有设定冲突和吃书") == "conflict_check"
    assert IntentRouter.detect_skill("帮我拆解这一章的场景 scene") == "scene_breakdown"
    assert IntentRouter.detect_skill("江炘的人设背景是什么") == "query_setting"
    assert IntentRouter.detect_skill("为什么流水线报错暂停了？") == "diagnose"
    assert IntentRouter.detect_skill("你好，请问今天天气怎么样") is None


def test_model_router():
    from novel_agent.assistant.router import ModelRouter

    # Fallback when no root_dir is provided
    assert ModelRouter.resolve_model_id("creative", None) is None

