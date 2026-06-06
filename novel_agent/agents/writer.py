from novel_agent.agents.base import PromptAgent
from novel_agent.logging_config import get_logger

logger = get_logger("agents.writer")


class WriterAgent(PromptAgent):
    def __init__(self, llm, prompts=None):
        super().__init__("writer", llm)
        self.prompts = prompts
        self.project_dir = None
        self.store = None

    def _get_platform_style(self) -> str:
        platform_name = "qidian"
        if self.project_dir:
            import json
            meta_path = self.project_dir / "config" / "project_meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    platform_name = meta.get("platform", "qidian")
                except Exception:
                    pass
        from novel_agent.control.platform_profiles import resolve_platform_profile
        profile = resolve_platform_profile(platform_name)
        
        style_prompt = profile.get("style_prompt", "")
        blacklist = profile.get("rules_blacklist", [])
        
        lines = [
            f"【目标平台：{profile['label']} 文风要求】",
            style_prompt
        ]
        if blacklist:
            lines.append("【文笔红线/避坑规避】")
            for rule in blacklist:
                lines.append(f"- {rule}")
        return "\n".join(lines)

    def write_scene(self, context: str) -> str:
        template = self.prompts.load("writer") if self.prompts else ""
        platform_style = self._get_platform_style()
        full_context = f"{template}\n\n## 平台风格指引\n{platform_style}\n\n## 待写作场景内容\n{context}".strip()
        return self.run(full_context).strip()

    async def awrite_scene(self, context: str) -> str:
        template = self.prompts.load("writer") if self.prompts else ""
        platform_style = self._get_platform_style()
        full_context = f"{template}\n\n## 平台风格指引\n{platform_style}\n\n## 待写作场景内容\n{context}".strip()
        res = await self.arun(full_context)
        return res.strip()
