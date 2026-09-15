"""Export engine and preflight inspector for Script Murder projects."""

from __future__ import annotations

import io
import json
import hashlib
import re
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..schemas import ScriptMurderWorkspace
from .validator import DeterministicValidator


def _safe_component(value: Any, fallback: str) -> str:
    """Return one ZIP path component; never allow separators or traversal tokens."""
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "")).replace("..", "_")
    text = text.strip(" .")[:100]
    return text or fallback


def _pdf_bytes(title: str, content: str) -> bytes:
    """Render a small printable PDF, with a safe ASCII fallback when no CJK font exists."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        font_name = "Helvetica"
        for candidate in (
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/simhei.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        ):
            if candidate.is_file():
                try:
                    pdfmetrics.registerFont(TTFont("ScriptMurderCJK", str(candidate)))
                    font_name = "ScriptMurderCJK"
                    break
                except Exception:
                    continue
        if font_name == "Helvetica":
            content = content.encode("ascii", "replace").decode("ascii")
        out = io.BytesIO()
        page = canvas.Canvas(out, pagesize=A4)
        width, height = A4
        page.setTitle(title[:200])
        page.setFont(font_name, 14)
        y = height - 48
        for line in (title + "\n\n" + content).splitlines():
            for wrapped in textwrap.wrap(line, width=64) or [""]:
                if y < 42:
                    page.showPage()
                    page.setFont(font_name, 10)
                    y = height - 42
                page.drawString(40, y, wrapped)
                y -= 16
        page.save()
        return out.getvalue()
    except Exception:
        # A valid minimal PDF is preferable to silently omitting the printable artifact.
        return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class ExportPreflightResult(BaseModel):
    can_export: bool = True
    blocker_count: int = 0
    warning_count: int = 0
    blocking_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ScriptMurderExporter:
    """Performs preflight checks and bundles production-ready mystery ZIP archives."""

    def __init__(self, workspace: ScriptMurderWorkspace, output_root: Optional[Path] = None):
        self.ws = workspace
        self.output_root = output_root

    def preflight_check(self) -> ExportPreflightResult:
        """Evaluate whether project is structurally intact and safe to export."""
        validator = DeterministicValidator(self.ws)
        report = validator.validate_all()

        blocking_reasons: List[str] = []
        warnings: List[str] = []

        # 1. Blockers from validator
        for issue in report.issues:
            if issue.severity in ("BLOCKER", "ERROR"):
                blocking_reasons.append(f"[{issue.code}] {issue.message}")
            elif issue.severity == "WARNING":
                warnings.append(f"[{issue.code}] {issue.message}")

        # 2. Basic completeness check
        if not self.ws.canon.victim or not self.ws.canon.killer:
            blocking_reasons.append("真相板缺少受害者或真凶设定")

        if len(self.ws.characters) == 0:
            blocking_reasons.append("尚未创建任何玩家角色")

        if len(self.ws.characters) != self.ws.meta.player_count:
            blocking_reasons.append(
                f"角色数量 ({len(self.ws.characters)}) 与企划人数 ({self.ws.meta.player_count}) 不匹配"
            )

        if len(self.ws.clues) == 0:
            blocking_reasons.append("尚未创建任何物证线索卡")

        if len(self.ws.conclusions) == 0:
            blocking_reasons.append("尚未创建任何关键推理结论")

        if len(self.ws.flow.rounds) == 0:
            blocking_reasons.append("游戏流程尚未编排任何轮次")

        if not self.ws.host_guide.strip():
            blocking_reasons.append("主持人手册尚未生成")

        for char in self.ws.characters:
            if not char.script_acts:
                blocking_reasons.append(f"角色 '{char.name}' 尚未生成玩家剧本")

        stale_nodes = sorted(k for k, v in self.ws.artifact_status.items() if v == "stale")
        if stale_nodes:
            blocking_reasons.append(f"派生节点已过期：{', '.join(stale_nodes)}")

        can_export = len(blocking_reasons) == 0

        return ExportPreflightResult(
            can_export=can_export,
            blocker_count=len(blocking_reasons),
            warning_count=len(warnings),
            blocking_reasons=blocking_reasons,
            warnings=warnings,
        )

    def build_zip_bytes(self) -> bytes:
        """Create structured in-memory ZIP package ready for hosting and printing."""
        preflight = self.preflight_check()
        if not preflight.can_export:
            raise ValueError(f"Export blocked: {'; '.join(preflight.blocking_reasons)}")

        buffer = io.BytesIO()
        title = self.ws.meta.title or "未命名剧本"
        safe_title = _safe_component(title, "未命名剧本")
        prefix = f"{safe_title}_剧本杀开本包/"

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 00 使用说明
            readme_content = (
                f"# 《{title}》· 剧本杀开本指南\n\n"
                f"## 基础参数\n"
                f"- **建议人数**：{self.ws.meta.player_count} 人\n"
                f"- **预估时长**：{self.ws.meta.duration_minutes} 分钟\n"
                f"- **题材风格**：{', '.join(self.ws.meta.genre)} / {', '.join(self.ws.meta.tone)}\n"
                f"- **故事背景**：{self.ws.meta.era} · {self.ws.meta.setting}\n\n"
                f"## 资料包目录\n"
                f"1. `01_主持人资料/`：含主持人全知手册、真相白皮书与时间总表，仅供 DM 阅读。\n"
                f"2. `02_角色剧本/`：每位玩家分册独立剧本，严禁互看。\n"
                f"3. `03_线索卡/`：按游戏轮次分文件夹存放，搜证时向对应玩家展示。\n"
                f"4. `04_公共资料/`：开场公开发布的故事背景与规则。\n"
                f"5. `05_结局/`：投凶后由主持人宣读的结局。\n"
                f"6. `source/`：结构化 JSON 数据，可重新导入墨局工坊继续编辑。\n"
            )
            zf.writestr(f"{prefix}00_开本主持人使用说明.md", readme_content.encode("utf-8"))

            # 01 主持人资料
            host_guide = self.ws.host_guide or (
                f"# 《{title}》主持人复盘与实操手册\n\n"
                f"## 核心真相\n"
                f"- **受害人**：{self.ws.canon.victim}\n"
                f"- **真凶**：{self.ws.canon.killer}\n"
                f"- **死因**：{self.ws.canon.cause_of_death}\n"
                f"- **作案手法**：{self.ws.canon.crime_method}\n"
                f"- **真实动机**：{self.ws.canon.true_motive}\n\n"
                f"## 关键事实流水线\n"
                + "\n".join([f"- **[{f.id}] {f.title}**（{f.occurred_at} / {f.location}）：{f.content}" for f in self.ws.canon.facts])
            )
            zf.writestr(f"{prefix}01_主持人资料/01_主持人手册.md", host_guide.encode("utf-8"))

            # 时间总表
            timeline_rows = ["# 二维时空与不在场证明对照总表\n\n| 时间 | 角色 | 真实行为 (Truth) | 声称在场证明 (Claimed) | 地点 |", "| :--- | :--- | :--- | :--- | :--- |"]
            for char in self.ws.characters:
                for ev in char.timeline:
                    timeline_rows.append(f"| {ev.time} | {char.name} | {ev.activity_real} | {ev.activity_claimed} | {ev.location} |")
            zf.writestr(f"{prefix}01_主持人资料/02_二维时空总时间表.md", "\n".join(timeline_rows).encode("utf-8"))

            # 02 角色剧本
            for idx, char in enumerate(self.ws.characters, 1):
                script_acts_text = "\n\n---\n\n".join([f"### {act}\n\n{text}" for act, text in char.script_acts.items()]) if char.script_acts else "（本幕暂未起草具体正文，请结合背景体验）"
                char_doc = (
                    f"# 《{title}》玩家剧本\n\n"
                    f"## 你的角色：{char.name}\n\n"
                    f"- **公开身份**：{char.public_identity}\n"
                    f"- **性别年龄**：{char.gender} · {char.age}岁\n"
                    f"- **你的欲望**：{char.desire}\n\n"
                    f"## 你的私密秘密（切勿向任何人主动展示本页）\n\n"
                    + "\n".join([f"- {s}" for s in char.secrets]) + "\n\n"
                    f"## 剧本文稿\n\n"
                    f"{script_acts_text}\n"
                )
                zf.writestr(
                    f"{prefix}02_角色剧本/{idx:02d}_{_safe_component(char.name, '角色')}_角色册.md",
                    char_doc.encode("utf-8"),
                )

            # 03 线索卡
            rounds_count = max([c.round for c in self.ws.clues] + [1])
            for r in range(1, rounds_count + 1):
                clues_in_round = [c for c in self.ws.clues if c.round == r]
                for clue in clues_in_round:
                    clue_doc = (
                        f"# 物证勘验单：[{clue.id}] {clue.title}\n\n"
                        f"- **发现轮次**：第 {clue.round} 轮\n"
                        f"- **搜证地点**：{clue.location or '案发现场'}\n"
                        f"- **物证类型**：{clue.clue_type}\n\n"
                        f"## 勘验记录\n\n"
                        f"{clue.content}\n"
                    )
                    safe_clue_id = _safe_component(clue.id, "clue")
                    safe_clue_title = _safe_component(clue.title, "线索")
                    zf.writestr(f"{prefix}03_线索卡/第{r}轮/{safe_clue_id}_{safe_clue_title}.md", clue_doc.encode("utf-8"))

            # 04 公共资料
            public_doc = (
                f"# 《{title}》故事背景与开场规则\n\n"
                f"{self.ws.flow.prologue or '深秋暴雨之夜，港口发生离奇命案，警报拉响，全场进入紧急搜证。'}\n\n"
                f"## 游戏须知\n"
                f"1. 严禁撕毁或私藏物证。\n"
                f"2. 除自身剧本允许撒谎的部分外，请尽量还原角色记忆。\n"
                f"3. 充分利用每轮公共讨论时间比对时间线。\n"
            )
            zf.writestr(f"{prefix}04_公共资料/01_故事背景与规则.md", public_doc.encode("utf-8"))

            # 05 结局
            ending_doc = (
                f"# 《{title}》游戏结局\n\n"
                f"## 结局一：真凶落网\n\n"
                f"{self.ws.flow.epilogue_killer or '真凶在无可辩驳的证据链前俯首认罪。'}\n\n"
                f"## 结局二：真凶逃脱\n\n"
                f"{self.ws.flow.epilogue_escape or '真凶误导成功，逍遥法外。'}\n"
            )
            zf.writestr(f"{prefix}05_结局/游戏结局复盘.md", ending_doc.encode("utf-8"))

            # Printable companions. Source Markdown remains the editable canonical projection.
            zf.writestr(
                f"{prefix}00_开本主持人使用说明.pdf",
                _pdf_bytes(title, readme_content),
            )
            zf.writestr(
                f"{prefix}01_主持人资料/01_主持人手册.pdf",
                _pdf_bytes(title + " · 主持人手册", host_guide),
            )
            zf.writestr(
                f"{prefix}01_主持人资料/02_二维时空总时间表.pdf",
                _pdf_bytes(title + " · 时间总表", "\n".join(timeline_rows)),
            )
            zf.writestr(
                f"{prefix}04_公共资料/01_故事背景与规则.pdf",
                _pdf_bytes(title + " · 公共资料", public_doc),
            )
            zf.writestr(
                f"{prefix}05_结局/游戏结局复盘.pdf",
                _pdf_bytes(title + " · 结局", ending_doc),
            )
            for idx, char in enumerate(self.ws.characters, 1):
                script_acts_text = "\n\n---\n\n".join(
                    [f"### {act}\n\n{text}" for act, text in char.script_acts.items()]
                )
                zf.writestr(
                    f"{prefix}02_角色剧本/{idx:02d}_{_safe_component(char.name, '角色')}_角色册.pdf",
                    _pdf_bytes(f"{title} · {char.name}", script_acts_text),
                )
            for r in range(1, rounds_count + 1):
                for clue in [c for c in self.ws.clues if c.round == r]:
                    zf.writestr(
                        f"{prefix}03_线索卡/第{r}轮/{_safe_component(clue.id, 'clue')}_{_safe_component(clue.title, '线索')}.pdf",
                        _pdf_bytes(f"{title} · {clue.id} {clue.title}", clue.content),
                    )

            # source 原始结构化数据
            zf.writestr(
                f"{prefix}source/project.json",
                self.ws.meta.model_dump_json(indent=2).encode("utf-8"),
            )
            zf.writestr(
                f"{prefix}source/truth_canon.json",
                self.ws.canon.model_dump_json(indent=2).encode("utf-8"),
            )
            zf.writestr(
                f"{prefix}source/characters.json",
                json.dumps([c.model_dump() for c in self.ws.characters], ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zf.writestr(
                f"{prefix}source/clues.json",
                json.dumps([c.model_dump() for c in self.ws.clues], ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zf.writestr(
                f"{prefix}source/conclusions.json",
                json.dumps([c.model_dump() for c in self.ws.conclusions], ensure_ascii=False, indent=2).encode("utf-8"),
            )
            zf.writestr(
                f"{prefix}source/flow.json",
                self.ws.flow.model_dump_json(indent=2).encode("utf-8"),
            )
            zf.writestr(f"{prefix}source/workspace.json", self.ws.model_dump_json(indent=2).encode("utf-8"))

            for idx, char in enumerate(self.ws.characters, 1):
                script = "\n\n---\n\n".join(
                    [f"### {act}\n\n{text}" for act, text in char.script_acts.items()]
                )
                zf.writestr(
                    f"{prefix}editable/characters/{idx:02d}_{_safe_component(char.name, '角色')}.md",
                    script.encode("utf-8"),
                )
            zf.writestr(f"{prefix}editable/host/host_guide.md", host_guide.encode("utf-8"))
            zf.writestr(f"{prefix}editable/markdown/workspace.json.md", self.ws.model_dump_json(indent=2).encode("utf-8"))

            manifest = {
                "schema_version": "1",
                "project_id": self.ws.meta.id,
                "source_revision": self.ws.revision,
                "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                "files": [
                    {"path": name, "sha256": hashlib.sha256(zf.read(name)).hexdigest()}
                    for name in zf.namelist()
                ],
            }
            zf.writestr(
                f"{prefix}source/export_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )

        return buffer.getvalue()
