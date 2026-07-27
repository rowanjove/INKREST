from typing import Any
from novel_agent.pipeline import PipelineConfig

from novel_agent.agents.chapter_planner import ChapterPlannerAgent
from novel_agent.agents.chapter_summary import ChapterSummaryAgent
from novel_agent.agents.chief_editor import ChiefEditorAgent
from novel_agent.agents.continuity_checker import ContinuityCheckerAgent
from novel_agent.agents.length_fix import LengthFixAgent
from novel_agent.agents.managing_editor import ManagingEditorAgent
from novel_agent.agents.planner import PlannerAgent
from novel_agent.agents.state_extractor import StateExtractorAgent
from novel_agent.agents.stitch_editor import StitchEditorAgent
from novel_agent.agents.style_editor import StyleEditorAgent
from novel_agent.agents.writer import WriterAgent
from novel_agent.agents.persona_reader import PersonaReaderAgent
from novel_agent.agents.auditor import AuditorAgent

def inject_agents(orchestrator: Any, config: PipelineConfig) -> None:
    """Initialize all workflow agents and attach them to the orchestrator."""
    overrides = {}
    if config.plugin_manager:
        overrides = config.plugin_manager.get_agent_overrides()

    factories = {
        "chief_editor": lambda: ChiefEditorAgent(config.get_llm("chief_editor"), orchestrator.prompts),
        "managing_editor": lambda: ManagingEditorAgent(config.get_llm("managing_editor"), orchestrator.prompts),
        "chapter_planner": lambda: ChapterPlannerAgent(config.get_llm("chapter_planner"), orchestrator.prompts),
        "planner": lambda: PlannerAgent(config.get_llm("planner"), orchestrator.prompts),
        "writer": lambda: WriterAgent(config.get_llm("writer"), orchestrator.prompts),
        "length_fix": lambda: LengthFixAgent(config.get_llm("length_fix"), orchestrator.prompts),
        "stitch_editor": lambda: StitchEditorAgent(config.get_llm("stitch_editor"), orchestrator.prompts),
        "style_editor": lambda: StyleEditorAgent(config.get_llm("style_editor"), orchestrator.prompts),
        "auditor": lambda: AuditorAgent(config.get_llm("auditor"), orchestrator.prompts),
        "state_extractor": lambda: StateExtractorAgent(config.get_llm("state_extractor"), orchestrator.prompts),
        "chapter_summary": lambda: ChapterSummaryAgent(config.get_llm("chapter_summary"), orchestrator.prompts),
        "continuity_checker": lambda: ContinuityCheckerAgent(config.get_llm("continuity_checker"), orchestrator.prompts),
        "persona_reader": lambda: PersonaReaderAgent(config.get_llm("persona_reader"), orchestrator.prompts, orchestrator.root_dir),
    }

    for role, plugin in overrides.items():
        if role in factories:
            factories[role] = lambda r=role, p=plugin: p.create_agent(config.get_llm(r), orchestrator.prompts)

    orchestrator.chief_editor = factories["chief_editor"]()
    orchestrator.managing_editor = factories["managing_editor"]()
    orchestrator.chapter_planner = factories["chapter_planner"]()
    orchestrator.planner = factories["planner"]()
    orchestrator.writer = factories["writer"]()
    orchestrator.length_fix = factories["length_fix"]()
    orchestrator.stitch_editor = factories["stitch_editor"]()
    orchestrator.style_editor = factories["style_editor"]()
    orchestrator.auditor = factories["auditor"]()
    orchestrator.auditor.root_dir = orchestrator.root_dir
    orchestrator.state_extractor = factories["state_extractor"]()
    orchestrator.chapter_summary_agent = factories["chapter_summary"]()
    orchestrator.continuity_checker = factories["continuity_checker"]()
    orchestrator.persona_reader = factories["persona_reader"]()
