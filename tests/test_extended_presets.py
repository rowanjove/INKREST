from pathlib import Path
from web.preset_manager import PresetManager


def test_preset_manager_loads_extended_themes():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    themes = pm.list_components("themes")
    theme_ids = {t["id"] for t in themes}

    # 验证严肃文学与经典类型小说已就绪
    assert "literary_realism" in theme_ids
    assert "mystery_detective" in theme_ids
    assert "hard_scifi" in theme_ids
    assert "cyberpunk_dystopia" in theme_ids
    assert "cthulhu_horror" in theme_ids
    assert "epic_fantasy" in theme_ids
    assert "magical_realism" in theme_ids
    assert "espionage_thriller" in theme_ids


def test_preset_manager_loads_narrative_mechanisms():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    mechanisms = pm.list_components("mechanisms")
    mech_ids = {m["id"] for m in mechanisms}

    # 验证结构与文学叙事机制已就绪
    assert "dual_timeline" in mech_ids
    assert "rashomon_effect" in mech_ids
    assert "unreliable_narrator" in mech_ids
    assert "ticking_clock" in mech_ids
    assert "reverse_mechanism" in mech_ids
    assert "mastermind_creator" in mech_ids


def test_preset_manager_loads_aesthetic_cool_points():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    cool_points = pm.list_components("cool_points")
    cp_ids = {c["id"] for c in cool_points}

    # 验证高阶智斗与严肃文学审美看点已就绪
    assert "deep_intellect" in cp_ids
    assert "cosmic_sublime" in cp_ids
    assert "tragic_fate" in cp_ids
    assert "moral_dilemma" in cp_ids
    assert "satire_humor" in cp_ids
    assert "epiphany_healing" in cp_ids


def test_preset_manager_composes_serious_literature_guide():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    # 组合一个严肃现实主义 + 双线交叉叙事 + 宿命悲凉 的纯文学项目指南
    guide = pm.compose_guide(
        channel="general",
        theme="literary_realism",
        mechanisms=["dual_timeline"],
        cool_points=["tragic_fate", "moral_dilemma"],
    )

    assert "严肃文学/现实主义" in guide
    assert "双线交叉叙事" in guide
    assert "宿命悲凉/时代车轮" in guide
    assert "道德困境/人性微光" in guide
    assert "---" in guide


def test_preset_manager_loads_japanese_light_novel_components():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    themes = {t["id"] for t in pm.list_components("themes")}
    mechs = {m["id"] for m in pm.list_components("mechanisms")}
    cools = {c["id"] for c in pm.list_components("cool_points")}

    # 验证日系轻小说流派
    assert "isekai_narou" in themes
    assert "romcom_school" in themes
    assert "villainess_noble" in themes
    assert "shin_honkaku" in themes
    assert "urban_ayakashi" in themes

    # 验证日系机制与看点
    assert "tsukkomi_voice" in mechs
    assert "party_removal" in mechs
    assert "villain_avoidance" in mechs
    assert "mono_no_aware" in cools
    assert "slow_life_healing" in cools
    assert "shuraba_tension" in cools

    # 测试日轻组合生成
    guide = pm.compose_guide(
        channel="male",
        theme="isekai_narou",
        mechanisms=["tsukkomi_voice", "party_removal"],
        cool_points=["slow_life_healing"],
    )
    assert "日系转生异世界" in guide
    assert "第一人称吐槽役漫才" in guide
    assert "退队流/悔不当初反转" in guide
    assert "异界慢生活/日常治愈" in guide


def test_preset_manager_loads_western_literature_components():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    themes = {t["id"] for t in pm.list_components("themes")}
    mechs = {m["id"] for m in pm.list_components("mechanisms")}
    cools = {c["id"] for c in pm.list_components("cool_points")}

    # 验证欧美文学流派
    assert "space_opera" in themes
    assert "hardboiled_noir" in themes
    assert "steampunk_victorian" in themes
    assert "dark_academia" in themes
    assert "wasteland_road" in themes
    assert "gothic_mansion" in themes

    # 验证欧美机制与看点
    assert "red_herring" in mechs
    assert "locked_room_isolated" in mechs
    assert "cynical_noir_voice" in mechs
    assert "grimdark_redemption" in cools
    assert "sublime_desolation" in cools

    # 测试欧美冷硬派侦探组合生成
    guide = pm.compose_guide(
        channel="male",
        theme="hardboiled_noir",
        mechanisms=["cynical_noir_voice", "red_herring"],
        cool_points=["grimdark_redemption"],
    )
    assert "欧美硬汉派/黑色侦探" in guide
    assert "冷硬犬儒第一人称独白" in guide
    assert "红鲱鱼假线索布阵" in guide
    assert "冷硬救赎/至暗微光" in guide


def test_preset_manager_loads_higashino_mystery_components():
    base_dir = Path(__file__).resolve().parents[1]
    pm = PresetManager(base_dir)

    themes = {t["id"] for t in pm.list_components("themes")}
    mechs = {m["id"] for m in pm.list_components("mechanisms")}
    cools = {c["id"] for c in pm.list_components("cool_points")}

    # 验证东野圭吾流派与专属机制
    assert "higashino_mystery" in themes
    assert "inverted_mystery" in mechs
    assert "symbiotic_bond" in mechs
    assert "ultimate_sacrifice_love" in cools

    # 测试东野圭吾《白夜行》/《嫌疑人X》式组合拼装
    guide = pm.compose_guide(
        channel="general",
        theme="higashino_mystery",
        mechanisms=["inverted_mystery", "symbiotic_bond"],
        cool_points=["ultimate_sacrifice_love", "tragic_fate"],
    )
    assert "东野圭吾式社会派悬疑" in guide
    assert "倒叙推理/动机迷宫" in guide
    assert "共生守护/暗影同行" in guide
    assert "极致献身/心碎真相" in guide
    assert "宿命悲凉/时代车轮" in guide


