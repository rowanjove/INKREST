"""ShanShan Assistant Controlled Agent Kernel.

Implements the controlled reasoning loop (Max Steps = 5) with:
1. Permission Level Enforcement (Level 0/1 auto, Level 3 proposal, Level 4/5 confirmation).
2. Plan -> Act paradigm for mutations and destructive ops.
3. Structured Tool Call parsing and execution.
4. Comprehensive Tool Call tracing (RunTracker).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

from pydantic import BaseModel, Field

from novel_agent.assistant.adapter.story_adapter import StoryAdapter
from novel_agent.assistant.context.resolver import StoryContextResolver
from novel_agent.assistant.memory.store import AssistantStore
from novel_agent.assistant.models import (
    ActiveEditorContext,
    AssistantPatch,
    CitationReference,
    EditorRange,
    PatchStatus,
    RunRecord,
    SourceType,
    ToolCallStep,
)
from novel_agent.assistant.patch.service import PatchService
from novel_agent.assistant.skills.registry import SkillRegistry, get_skill_registry
from novel_agent.assistant.tools.builtin_tools import register_builtin_tools
from novel_agent.assistant.tools.registry import (
    PermissionLevel,
    ToolDefinition,
    ToolRegistry,
    get_tool_registry,
)
from novel_agent.assistant.trace.run_tracker import RunTracker


class KernelRunResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    run_id: str
    reply: str = ""
    patch: Optional[Dict[str, Any]] = None
    action_proposal: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    citations: List[CitationReference] = Field(default_factory=list)
    steps: List[ToolCallStep] = Field(default_factory=list)
    total_elapsed_ms: int = 0
    status: str = "completed"


class ShanShanKernel:
    MAX_STEPS = 5

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        tool_registry: Optional[ToolRegistry] = None,
        story_adapter: Optional[StoryAdapter] = None,
        patch_service: Optional[PatchService] = None,
        store: Optional[AssistantStore] = None,
    ):
        self.root_dir = Path(root_dir) if root_dir else None
        self.store = store or AssistantStore(self.root_dir)
        self.story_adapter = story_adapter or StoryAdapter(self.root_dir)
        self.patch_service = patch_service or PatchService(self.root_dir)
        self.tool_registry = tool_registry or register_builtin_tools(
            registry=ToolRegistry(),
            story_adapter=self.story_adapter,
            patch_service=self.patch_service,
            root_dir=self.root_dir,
        )
        self.tracker = RunTracker(self.store)

    def _format_tools_description(self) -> str:
        defs = self.tool_registry.list_definitions()
        lines = ["可用的受控工具列表："]
        for d in defs:
            level_str = "自动允许" if d.permission_level <= PermissionLevel.LEVEL_1_SEARCH else "需用户确认"
            lines.append(f"- `{d.name}`: {d.description} [权限等级: {d.permission_level.value}, {level_str}]")
        return "\n".join(lines)

    def _parse_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract tool call JSON from ===TOOL_CALL=== block."""
        if "===TOOL_CALL===" not in text:
            return None
        try:
            parts = text.split("===TOOL_CALL===", 1)[1]
            # Match JSON object
            json_match = re.search(r'\{.*\}', parts, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if isinstance(data, dict) and "name" in data:
                    return data
        except Exception:
            pass
        return None

    def _parse_extra_blocks(self, text: str) -> tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        """Parses ===PATCH===, ===ACTIONS===, and ===SUGGESTIONS=== from reply."""
        patch_data = None
        actions: List[Dict[str, Any]] = []
        suggestions: List[str] = []

        # Parse PATCH
        if "===PATCH===" in text:
            parts = text.split("===PATCH===", 1)
            text = parts[0]
            rest = parts[1]
            match = re.search(r'\{.*?\}', rest, re.DOTALL)
            if match:
                try:
                    patch_data = json.loads(match.group(0))
                except Exception:
                    pass
            text += "\n" + rest[match.end():] if match else rest

        # Parse ACTIONS
        if "===ACTIONS===" in text:
            parts = text.split("===ACTIONS===", 1)
            text = parts[0]
            rest = parts[1]
            match = re.search(r'\[.*?\]', rest, re.DOTALL)
            if match:
                try:
                    actions = json.loads(match.group(0))
                except Exception:
                    pass
            text += "\n" + rest[match.end():] if match else rest

        # Parse SUGGESTIONS
        if "===SUGGESTIONS===" in text:
            parts = text.split("===SUGGESTIONS===", 1)
            text = parts[0]
            rest = parts[1]
            match = re.search(r'\[.*?\]', rest, re.DOTALL)
            if match:
                try:
                    suggestions = json.loads(match.group(0))
                except Exception:
                    pass

        return text.strip(), patch_data, actions, suggestions

    async def run(
        self,
        user_message: str,
        editor_context: Optional[ActiveEditorContext] = None,
        skill_id: Optional[str] = None,
        project_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        llm_caller: Optional[Callable[[str], Coroutine[Any, Any, str]]] = None,
        user_confirmed: bool = False,
        confirmed_action: Optional[Dict[str, Any]] = None,
        confirm_run_id: Optional[str] = None,
        max_steps: Optional[int] = None,
    ) -> KernelRunResult:
        """Executes a controlled agent run for ShanShan."""
        start_time = time.perf_counter()
        run_record = self.tracker.start_run(
            project_id=project_id,
            thread_id=thread_id,
            skill_id=skill_id,
        )
        run_id = run_record.id
        steps_limit = min(max_steps or self.MAX_STEPS, self.MAX_STEPS)

        # 1. Handle pre-confirmed action execution if user explicitly clicked Confirm
        if user_confirmed:
            source = self.tracker.get_run(confirm_run_id) if confirm_run_id else None
            proposal: Optional[Dict[str, Any]] = None
            if source is not None:
                for step in reversed(list(source.steps or [])):
                    if getattr(step, "status", "") != "requires_confirmation":
                        continue
                    output = step.tool_output if isinstance(step.tool_output, dict) else {}
                    proposal = output.get("proposal") if isinstance(output, dict) else None
                    if not isinstance(proposal, dict):
                        proposal = {
                            "name": step.tool_name,
                            "arguments": step.tool_input or {},
                        }
                    break
            if not isinstance(proposal, dict) or not proposal.get("name"):
                failed = self.tracker.finish_run(
                    run_id, status="failed", output_text="没有可确认的待执行操作"
                )
                return KernelRunResult(
                    run_id=run_id,
                    reply="没有可确认的待执行操作",
                    steps=list(failed.steps) if failed else [],
                    total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                    status="failed",
                )
            if confirmed_action:
                if str(confirmed_action.get("name") or "") != str(proposal.get("name") or ""):
                    failed = self.tracker.finish_run(
                        run_id, status="failed", output_text="确认操作与待执行提议不一致"
                    )
                    return KernelRunResult(
                        run_id=run_id,
                        reply="确认操作与待执行提议不一致",
                        steps=list(failed.steps) if failed else [],
                        total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                        status="failed",
                    )
                client_args = confirmed_action.get("arguments")
                if client_args is not None and json.dumps(
                    client_args, sort_keys=True, ensure_ascii=False
                ) != json.dumps(proposal.get("arguments") or {}, sort_keys=True, ensure_ascii=False):
                    failed = self.tracker.finish_run(
                        run_id, status="failed", output_text="确认参数与待执行提议不一致"
                    )
                    return KernelRunResult(
                        run_id=run_id,
                        reply="确认参数与待执行提议不一致",
                        steps=list(failed.steps) if failed else [],
                        total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                        status="failed",
                    )
            tool_name = proposal.get("name")
            tool_args = proposal.get("arguments") or {}
            registered = self.tool_registry.get(tool_name)
            if not registered:
                err_msg = f"待确认工具不可用: {tool_name}"
                self.tracker.finish_run(run_id, status="failed", output_text=err_msg)
                return KernelRunResult(
                    run_id=run_id,
                    reply=err_msg,
                    total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                    status="failed",
                )
            if registered:
                step_start = time.perf_counter()
                try:
                    res = await registered.execute(**tool_args)
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    step = self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=res,
                        permission_level=registered.definition.permission_level.value,
                        status="success",
                        elapsed_ms=elapsed_ms,
                    )
                    out_text = f"已成功执行操作: {tool_name}\n结果: {json.dumps(res, ensure_ascii=False)}"
                    self.tracker.finish_run(run_id, status="completed", output_text=out_text)
                    return KernelRunResult(
                        run_id=run_id,
                        reply=out_text,
                        steps=[step],
                        total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                        status="completed",
                    )
                except Exception as exc:
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    step = self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=None,
                        permission_level=registered.definition.permission_level.value,
                        status="error",
                        elapsed_ms=elapsed_ms,
                        error=str(exc),
                    )
                    err_msg = f"执行操作 {tool_name} 失败: {str(exc)}"
                    self.tracker.finish_run(run_id, status="failed", output_text=err_msg)
                    return KernelRunResult(
                        run_id=run_id,
                        reply=err_msg,
                        steps=[step],
                        total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                        status="failed",
                    )

        # 2. Setup Context Resolver and bundle
        resolver = StoryContextResolver(self.story_adapter)
        context_bundle = resolver.resolve(user_message, editor_context, skill_id)

        # 3. Agent Execution Loop
        conversation_history: List[str] = [
            f"用户指令: {user_message}",
            f"上下文参考:\n{context_bundle.formatted_prompt_block}",
            self._format_tools_description(),
            "规则：如果你需要查证信息，请只输出 ===TOOL_CALL=== JSON。若信息充足，直接给出回答。",
        ]

        final_reply = ""
        patch_res: Optional[Dict[str, Any]] = None
        action_proposal: Optional[Dict[str, Any]] = None
        actions: List[Dict[str, Any]] = []
        suggestions: List[str] = []

        for step_idx in range(steps_limit):
            if not llm_caller:
                final_reply = f"已通过受控中枢完成初步分析。当前涉及参考: {', '.join(context_bundle.chips) if context_bundle.chips else '当前项目'}"
                break

            # Prompt LLM
            prompt = "\n\n".join(conversation_history)
            try:
                response = await llm_caller(prompt)
            except Exception as e:
                final_reply = f"模型调用中断: {str(e)}"
                break

            # Check if LLM requested a tool call
            tool_call = self._parse_tool_call(response)
            if not tool_call:
                # No tool call; final response generated
                clean_text, patch_from_text, acts, suggs = self._parse_extra_blocks(response)
                final_reply = clean_text
                if patch_from_text:
                    patch_res = patch_from_text
                actions.extend(acts)
                suggestions.extend(suggs)
                break

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            registered = self.tool_registry.get(tool_name)

            if not registered:
                conversation_history.append(f"===TOOL_RESULT===\n工具 '{tool_name}' 不存在，请换用有效工具或直接回答。")
                continue

            permission = registered.definition.permission_level
            step_start = time.perf_counter()

            # --- Permission Level Check ---
            # Level 0 & 1: Auto execute and continue reasoning
            if permission <= PermissionLevel.LEVEL_1_SEARCH:
                try:
                    tool_res = await registered.execute(**tool_args)
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=tool_res,
                        permission_level=permission.value,
                        status="success",
                        elapsed_ms=elapsed_ms,
                    )
                    res_str = json.dumps(tool_res, ensure_ascii=False)
                    conversation_history.append(f"===TOOL_RESULT===\n工具 {tool_name} 返回:\n{res_str}")
                    continue
                except Exception as e:
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=None,
                        permission_level=permission.value,
                        status="error",
                        elapsed_ms=elapsed_ms,
                        error=str(e),
                    )
                    conversation_history.append(f"===TOOL_RESULT===\n工具 {tool_name} 执行失败: {str(e)}")
                    continue

            # --- Level 3: Proposal Tool (e.g. propose_text_patch) ---
            if permission == PermissionLevel.LEVEL_3_PROPOSAL:
                try:
                    tool_res = await registered.execute(**tool_args)
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=tool_res,
                        permission_level=permission.value,
                        status="requires_confirmation",
                        elapsed_ms=elapsed_ms,
                    )
                    patch_res = tool_res
                    final_reply = f"已为第 {tool_args.get('chapter_id')} 章生成修改提议，请在下方审阅确认："
                    break
                except Exception as e:
                    elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                    self.tracker.record_step(
                        run_id=run_id,
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=None,
                        permission_level=permission.value,
                        status="error",
                        elapsed_ms=elapsed_ms,
                        error=str(e),
                    )
                    final_reply = f"生成修改提议失败: {str(e)}"
                    break

            # --- Level 4 & 5: Ops / Mutation Tools (retry_chapter, rerun_gate, etc.) ---
            # Plan -> Act paradigm: Requires explicit user confirmation
            action_proposal = {
                "name": tool_name,
                "arguments": tool_args,
                "description": registered.definition.description,
                "permission_level": permission.value,
                "requires_confirmation": True,
            }
            elapsed_ms = int((time.perf_counter() - step_start) * 1000)
            self.tracker.record_step(
                run_id=run_id,
                tool_name=tool_name,
                tool_input=tool_args,
                tool_output={"proposal": action_proposal},
                permission_level=permission.value,
                status="requires_confirmation",
                elapsed_ms=elapsed_ms,
            )
            final_reply = f"准备执行操作「{registered.definition.description}」，此操作将影响生产状态或正文，请确认是否执行："
            actions.append({
                "label": f"确认执行: {registered.definition.name}",
                "type": "kernel_confirm_action",
                "payload": action_proposal,
            })
            break

        # 4. Finish run and wrap result
        total_elapsed = int((time.perf_counter() - start_time) * 1000)
        final_status = "requires_confirmation" if action_proposal else "completed"
        finished_run = self.tracker.finish_run(
            run_id=run_id,
            status=final_status,
            output_text=final_reply,
        )

        return KernelRunResult(
            run_id=run_id,
            reply=final_reply,
            patch=patch_res,
            action_proposal=action_proposal,
            actions=actions,
            suggestions=suggestions,
            citations=context_bundle.citations,
            steps=finished_run.steps if finished_run else [],
            total_elapsed_ms=total_elapsed,
            status=final_status,
        )
