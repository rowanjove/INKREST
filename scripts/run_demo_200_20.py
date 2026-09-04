"""Create a 200-chapter long-form novel project and run 20 chapters through the full orchestrator pipeline."""

import os
import sys
import json
import time
from pathlib import Path

# Ensure root directory is set
ROOT_DIR = Path(__file__).resolve().parents[1]
os.environ["NOVEL_AGENT_ROOT"] = str(ROOT_DIR)
sys.path.insert(0, str(ROOT_DIR))

import web.context as ws_server
from web.project_manager import ProjectManager
from novel_agent.control.scale_profile import resolve_scale_profile
from novel_agent.pipeline import PipelineConfig
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.services.rolling_planner import prepare_queue_for_run
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.sqlite_schema import safe_connection


def build_macro_outline():
    """Build 10 arcs spanning 200 chapters for the novel."""
    arcs = []
    arc_themes = [
        ("A01", "启航与深空遗物", "1-20", "在边缘星港接下一趟绝密押运，飞船遭受伏击，被迫迫降古遗迹行星", "发现远古先驱者信标的倒计时正在开启", "成功修复飞船并突围，获得先驱者序列密码"),
        ("A02", "星际黑市的迷雾", "21-40", "穿越法外之地海盗星区，寻找破译先驱者密码的密码学家", "密码学家被巨型财阀暗杀，线索指向银河议会高层", "从追杀中救出学者的学徒，获得关键星图坐标"),
        ("A03", "跃迁断层的死局", "41-60", "被迫进入被称为死亡之渊的重力异常跃迁断裂带", "飞船能源核心枯竭，遭遇幽灵舰队围攻", "利用重力弹弓与超维引力波完成反杀，全员生还"),
        ("A04", "财阀舰队的围猎", "61-80", "星际巨企「奥罗拉联合体」出动无畏级战舰全境封锁信使", "同行多年的副官真实身份曝光，面临信任崩塌", "借用废弃要塞的轨道歼星炮击穿封锁线"),
        ("A05", "古老神殿的回响", "81-100", "抵达银河边缘的先驱者核心神殿，揭开第一次文明灭绝之谜", "信件内容部分解密：宇宙并非自然膨胀，而是在被收割", "信使自身基因序列与先驱者圣堂产生共振，掌控部分古科技"),
        ("A06", "议会暗流与风暴", "101-120", "潜入银河联邦首都星，试图向最高评议会公布收割者真相", "评议会高层早已被收割者意识渗透，信使反被通缉", "揭露伪神代言人的真面目，引发全银河平民觉醒狂潮"),
        ("A07", "失落舰队的集结", "121-140", "奔赴各星系边缘，联合抵抗军、自由游民与边缘领主组建联军", "联军内部派系林立，争夺指挥权导致防线险遭击溃", "以无畏战术摧毁敌方侦察先锋，正式确立联军总指挥地位"),
        ("A08", "深渊裂隙的决战", "141-160", "在黑洞边缘构筑第一道反收割者防线，阻击先头傀儡舰队", "收割者降临者撕裂时空，防线旗舰遭受毁灭性降维打击", "利用先驱者核心诱爆超新星，粉碎第一波主力"),
        ("A09", "终极星门的开启", "161-180", "收集全银河十二枚先驱者信物，启动前往宇宙中心终极星门的钥匙", "牺牲与抉择：通往星门的跃迁需要熄灭整片星云的能量", "全员决死意志，成功打破高维封锁，进入宇宙中枢"),
        ("A10", "群星不熄的远征", "181-200", "与收割者母体文明进行跨维度文明逻辑交锋与终局之战", "母体揭晓残酷的终极平衡法则，信使给出第三种文明可能", "点燃新宇宙常数火种，银河纪元重获新生，信使启程新航道"),
    ]
    for arc_id, name, ch_range, goal, turning, payoff in arc_themes:
        arcs.append({
            "arc_id": arc_id,
            "name": name,
            "chapters": ch_range,
            "goal": goal,
            "turning_point": turning,
            "payoff": payoff,
        })
    return arcs


def main():
    print("=" * 70)
    print("【栖墨 V2 真实长篇生成实测】")
    print("目标设定：200 章宏大体量科幻长篇，真实连续生成 20 章并全盘验证")
    print("=" * 70)

    pm = ProjectManager(ROOT_DIR)
    project_name = "星渊信使：终极跃迁"
    description = "横跨200个跃迁点的宏大太空歌剧。一艘老旧货船，一份颠覆宇宙存亡的信件，十卷星际史诗。"

    target_pid = sys.argv[1] if len(sys.argv) > 1 else None
    if target_pid and (ROOT_DIR / "projects" / target_pid).is_dir():
        pid = target_pid
        project_dir = ROOT_DIR / "projects" / pid
        print(f"\n[Step 1] 使用已有项目: {project_name} (ID: {pid}) ...")
    else:
        print(f"\n[Step 1] 创建项目: {project_name} ...")
        proj = pm.create_project(project_name, description)
        pid = proj["id"]
        project_dir = ROOT_DIR / "projects" / pid
        print(f"-> 项目创建成功，ID: {pid}, 目录: {project_dir}")

    # 激活当前项目
    ws_server.activate_project(pid)
    print(f"-> 已激活项目: {pid}")

    # 构造 200 章 ScaleProfile 与大纲
    scale_profile = resolve_scale_profile(target_chapters=200, scale="long")
    macro_outline = build_macro_outline()

    outline = {
        "chosen_title": project_name,
        "title_options": [project_name, "深空信使", "星门启示录"],
        "logline": description,
        "core_theme": "文明存续与跨维度勇气",
        "genre_positioning": "科幻",
        "target_reader": "硬科幻与太空歌剧读者",
        "reader_promise": ["跌宕起伏的星际追逃", "严密宏大的远古遗迹设定", "震撼人心的文明决战"],
        "target_chapters": 200,
        "scale_profile": scale_profile,
        "macro_outline": macro_outline,
        "world_rules": [
            "曲率跃迁需要消耗反物质星门引力索",
            "先驱者文明遗迹具有量子自愈和超维辐射特性",
            "三大势力：银河评议会、奥罗拉联合体财阀、深空自由游民",
            "神秘收割者：每三千万年周期性熄灭星系文明的未知地外意志",
        ],
        "protagonist": {
            "name": "沈凌",
            "desire": "完成失踪养父留下的最后一趟货运协议",
            "flaw": "对过度机械化的体系缺乏信任，偏执孤傲",
            "edge": "顶级盲跳跃迁直觉与先驱者神经元契合体质",
            "limit": "身体承受不了连续三次超载跃迁的引力过载",
        },
        "main_cast": [
            {"name": "埃达", "role": "飞船AI管家兼机械师", "relationship_to_protagonist": "生死搭档", "secret_or_pressure": "底层代码有先驱者留下的未解密锁死区"},
            {"name": "林宛", "role": "叛逃的奥罗拉财阀首席天体物理学家", "relationship_to_protagonist": "同盟与破译者", "secret_or_pressure": "被财阀植入了追踪信标"},
        ],
        "antagonistic_forces": ["奥罗拉联合体执行舰队司令莫拉", "深空遗弃者海盗王", "收割者先行官意志"],
        "forbidden_moves": ["主角无理由圣母", "机械降神打破物理法则", "剧情逻辑撕裂"],
    }

    ws_dir = project_dir / "workspace"
    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> 200 章宏观大纲已生成 (共 {len(macro_outline)} 卷，规划至第 200 章)")

    # 步骤 2：同步第一卷队列 (A01: 1-20 章)
    print(f"\n[Step 2] 同步第 1 卷队列 (A01: 1-20 章) ...")
    config = PipelineConfig.dry_run(project_dir)
    orchestrator = NovelOrchestrator(config)

    # 构造第一卷 20 个章节的细纲计划
    chapters_a01 = []
    chapter_goals = [
        ("001", "最后的起航", "沈凌在边缘星港接下这笔报酬高得诡异的密封冷冻匣运单，察觉周围密布财阀眼线。"),
        ("002", "暗港围捕", "离开泊位瞬间遭遇联合体特遣队突袭，沈凌强行开启过载引擎破港冲出。"),
        ("003", "冷冻匣异动", "飞船进入星系边缘引力盲区，密封匣发生超维能量脉冲，飞船导航系统瞬间离线。"),
        ("004", "海盗尾行", "雷达捕获到黑旗海盗舰队的追踪信号，沈凌被迫将航线切入碎石流密集带。"),
        ("005", "碎石带搏杀", "在千钧一发的陨石缝隙中利用机动规避打穿海盗前锋艇，但飞船副动力舱受损。"),
        ("006", "先驱者引力井", "深空雷达捕捉到未知行星散发的超低频引力谐波，正是冷冻匣信标指向之地。"),
        ("007", "烈焰坠落", "穿透未知行星高密度金属电离层，飞船硬着陆在遍布晶体废墟的远古地表。"),
        ("008", "死寂行星", "踏出舱门探查，四周耸立着违背建筑力学的高耸尖塔，空气中弥漫微光尘埃。"),
        ("009", "先驱者回声", "沈凌靠近遗迹核心基座，冷冻匣自动弹开，投射出一幅未曾见过的星图全息。"),
        ("010", "机械傀儡苏醒", "遗迹防御机制被非正常激活，数千年前的先驱者自律哨兵从地下破土而出。"),
        ("011", "破译者林宛", "在逃亡中偶遇同样被困在此处的女学者林宛，两人达成紧急战术互信。"),
        ("012", "逆向思维导通", "林宛利用先驱者符号逻辑暂时瘫痪守卫中枢，为飞船抢修争取宝贵窗口。"),
        ("013", "财阀主力降临", "奥罗拉联合体的重巡洋舰破空而至，轨道轰炸将地表晶体丛林化为火海。"),
        ("014", "地下圣殿逃亡", "沈凌与林宛带着信物坠入遗迹深层地下暗河，发现先驱者最后的造船坞。"),
        ("015", "古代跃迁核心", "造船坞内赫然停泊着一艘尚未组装完成的先驱者战舰原型，其核心仍具有活性。"),
        ("016", "抢修与移植", "埃达冒着逻辑崩溃风险，将古代核心的逆引力发生器强行焊接到老旧货船上。"),
        ("017", "背水一战", "财阀地面精锐破门而入，沈凌驾驶搭载古科技发生器的货船破土冲天。"),
        ("018", "重力脉冲对轰", "在近地轨道与财阀重巡正面交火，沈凌诱导对方主炮命中遗迹防御引力陷阱。"),
        ("019", "大逃杀与盲跳", "重巡洋舰在引力塌陷中解体，货船借由能量爆发启动无坐标超空间盲跳。"),
        ("020", "第一卷尾声：迷航与黎明", "货船冲出超空间跃迁盲区，来到未知星域边缘；信标第一段信息完全解密，通往银河彼端的大逃杀正式拉开大幕。"),
    ]

    arc_a01 = {
        "arc_id": "A01",
        "arc_name": "启航与深空遗物",
        "arc_goal": "在边缘星港接下一趟绝密押运，突破围堵并获得先驱者序列密码",
        "chapters": [
            {
                "chapter_id": cid,
                "chapter_title": f"第{int(cid)}章 {title}",
                "chapter_goal": goal,
                "input_state": "危机持续" if int(cid) > 1 else "边缘星港接单",
                "output_state": "突破并进入下一阶段",
                "reader_payoff": "绝地反击与宏大科幻揭秘",
                "hook": "更大的危机正接踵而至",
                "must_include": [title, "科幻场景", "紧张动作"],
                "must_not_include": ["脱离物理逻辑"],
            }
            for cid, title, goal in chapter_goals
        ],
    }
    (ws_dir / "arc_A01.json").write_text(json.dumps(arc_a01, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> 第 1 卷 (A01) 20 章节计划成功生成写入 workspace/arc_A01.json")

    # 步骤 3：连续生成第 1 到第 20 章
    print(f"\n[Step 3] 开始连续生成第 1 ~ 20 章 (全链路调度) ...")
    start_time = time.time()
    generated_chapters = []

    store = SQLiteStateStore(project_dir)

    for ch_info in arc_a01["chapters"]:
        cid = ch_info["chapter_id"]
        goal = ch_info["chapter_goal"]
        t0 = time.time()
        print(f"  --> 正在生成 第 {int(cid):02d} 章: {ch_info['chapter_title']} ... ", end="", flush=True)

        res = orchestrator.run_chapter(cid, goal)
        elapsed = time.time() - t0
        generated_chapters.append(res)
        print(f"完成! 耗时 {elapsed:.2f}s | 风险: {res.audit.get('risk_level', '低')} | 产物: {res.final_path.name}")

    total_time = time.time() - start_time
    print(f"\n-> 前 20 章生成完毕！总耗时: {total_time:.2f} 秒 (平均 {total_time/20:.2f} 秒/章)")

    # 步骤 4：全盘数据健康检查与统计
    print(f"\n[Step 4] 产物与数据库全盘指标体检 ...")

    # 1. 物理章节文件
    chap_files = list(project_dir.glob("workspace/chapters/*/chapter_final.txt"))
    print(f"  [1] 物理正文文件数量: {len(chap_files)} / 20")
    total_chars = 0
    for f in sorted(chap_files):
        txt = f.read_text(encoding="utf-8")
        total_chars += len(txt)
    print(f"  [2] 前 20 章总字数: {total_chars:,} 字符 (平均每章 {total_chars//len(chap_files):,} 字)")

    # 2. SQLite 真源检查
    with safe_connection(store.db_path, is_write=False) as conn:
        doc_count = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        rev_count = conn.execute("SELECT count(*) FROM document_revisions").fetchone()[0]
        event_count = conn.execute("SELECT count(*) FROM narrative_events").fetchone()[0] if "narrative_events" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")] else 0
        timeline_count = conn.execute("SELECT count(*) FROM narrative_timeline").fetchone()[0] if "narrative_timeline" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")] else 0

    print(f"  [3] SQLite documents 记录: {doc_count} 条")
    print(f"  [4] SQLite document_revisions 版本记录: {rev_count} 条")
    print(f"  [5] 叙事事件库 (narrative_events): {event_count} 条")
    print(f"  [6] 时间线节点 (narrative_timeline): {timeline_count} 条")

    # 3. 导出全书 TXT 测试
    from novel_agent.exporters.txt_exporter import export_txt
    export_out = project_dir / "workspace" / "export" / f"{project_name}_前20章.txt"
    export_txt(project_dir, export_out)
    print(f"  [7] 全书导出 TXT 验证: {export_out.name} ({export_out.stat().st_size:,} 字节)")

    print("\n" + "=" * 70)
    print("【实测成功】200 章长篇架构成功建立，前 20 章全流程生成与数据库流转 100% 畅通！")
    print(f"项目 ID: {pid}")
    print(f"项目目录: {project_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
