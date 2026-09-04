from novel_agent.services.chekhov_radar import generate_radar_report, scan_threads_dormancy


def test_chekhov_radar_dormancy_detection():
    # 模拟在第 30 章时的线索状态
    threads = [
        # 线索 1：第 28 章才刚提及（活跃）
        {"id": "T01", "title": "宗门大比的暗箱操作", "status": "open", "last_chapter": 28},
        # 线索 2：第 22 章提及（潜伏温眠：距离 8 章）
        {"id": "T02", "title": "后山禁地的神秘残魂", "status": "open", "last_chapter": 22},
        # 线索 3：第 5 章埋下后至今未提及（严重悬空：距离 25 章！）
        {"id": "T03", "title": "生母留下的青铜钥匙", "status": "open", "last_chapter": 5},
        # 线索 4：已经完结/关闭的线索（应被忽略）
        {"id": "T04", "title": "新手村退婚风波", "status": "closed", "last_chapter": 3},
    ]

    signals = scan_threads_dormancy(threads, current_chapter=30)
    # T04 已关闭，不出现在雷达中
    assert len(signals) == 3

    # 排序：距离最大的排在最前
    assert signals[0].thread_id == "T03"
    assert signals[0].dormant_distance == 25
    assert signals[0].status == "dangling_critical"
    assert "悬空契诃夫之枪警告" in signals[0].recovery_suggestion

    assert signals[1].thread_id == "T02"
    assert signals[1].status == "simmering"

    assert signals[2].thread_id == "T01"
    assert signals[2].status == "active"


def test_chekhov_radar_report_generation():
    threads = [
        {"id": "T01", "title": "神秘玉佩的异动", "status": "open", "last_chapter": 2},
    ]
    # 在第 20 章时扫描（沉睡 18 章）
    signals = scan_threads_dormancy(threads, current_chapter=20)
    report = generate_radar_report(signals)

    assert report["pass"] is False
    assert report["critical_count"] == 1
    assert len(report["recommendations"]) == 1
    assert "神秘玉佩的异动" in report["recommendations"][0]
