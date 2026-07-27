"""Background task manager for running chapters asynchronously using asyncio."""

import asyncio
import threading
import uuid
import contextvars
import json
from functools import partial
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from novel_agent.logging_config import get_logger
from novel_agent.domain.tasks import TaskRecord, TaskStatus, TaskType
from novel_agent.orchestrator import NovelOrchestrator
from novel_agent.pipeline import PipelineConfig, assert_llm_ready
from web.task_batch import run_chapter_batch
from web.task_progress import handle_progress_message
from novel_agent.progress import progress_handlers
from novel_agent.state.sqlite_store import SQLiteStateStore
from novel_agent.state.task_repository import TaskConflictError

task_id_var = contextvars.ContextVar("task_id", default=None)
logger = get_logger("tasks")


def _is_auto_resumable_single_chapter_task(task: Dict[str, Any]) -> bool:
    """Return true only for pending standard single-chapter generation tasks."""
    return bool(
        task.get("chapter_id")
        and task.get("task_type") == TaskType.CHAPTER.value
        and task.get("mode", "standard") == "standard"
        and task.get("status") == TaskStatus.PENDING.value
    )


# Delay import to avoid circular imports during startup
def _get_autopilot_helper():
    from web.tasks_autopilot import submit_novel_continue_helper
    return submit_novel_continue_helper



class TaskManager:
    def __init__(self, root_dir: Path, max_concurrent: Optional[int] = None):
        self.root_dir = Path(root_dir)
        self.project_id = self.root_dir.name
        self.store = SQLiteStateStore(self.root_dir)
        self.task_repository = self.store.task_repository
        if max_concurrent is None:
            from novel_agent.services.execution_policy import resolve_max_concurrent_chapters

            max_concurrent = resolve_max_concurrent_chapters(self.root_dir)
        self._max_concurrent = max(1, min(int(max_concurrent), 8))
        self._semaphores_by_loop: Dict[int, asyncio.Semaphore] = {}
        self._locks_by_loop: Dict[int, asyncio.Lock] = {}
        self._novel_batch_lock = threading.Lock()

        # In-memory tracking of active asyncio Task objects
        self._running_tasks: Dict[str, asyncio.Task] = {}
        # In-memory mapping from chapter_id -> active task_id
        self._running_chapters: Dict[str, str] = {}
        self._claim_tokens: Dict[str, str] = {}
        
        # Set of aborted task IDs (speedy synchronous check for progress polling)
        self._aborted_tasks = set()
        
        self._startup_cleanup()
        self._wrap_store_ws_notify()

        try:
            loop = asyncio.get_running_loop()
            self._queue_loop_task = loop.create_task(self._run_pending_tasks_loop())
        except RuntimeError:
            self._queue_loop_task = None

    async def _run_with_progress_context(
        self,
        task_id: str,
        awaitable_factory: Callable[[], Awaitable[Any]],
    ) -> Any:
        with progress_handlers(
            self._on_progress_emitted,
            lambda: self.is_aborted(task_id),
            project_id=self.project_id,
            task_id=task_id,
        ):
            return await awaitable_factory()

    def _create_task(
        self,
        task_id: str,
        awaitable_factory: Callable[[], Awaitable[Any]],
    ) -> asyncio.Task:
        return asyncio.get_running_loop().create_task(
            self._run_with_progress_context(task_id, awaitable_factory)
        )

    def _semaphore_for_loop(self) -> asyncio.Semaphore:
        """One semaphore per running event loop (TestClient / worker threads)."""
        loop = asyncio.get_running_loop()
        key = id(loop)
        sem = self._semaphores_by_loop.get(key)
        if sem is None:
            sem = asyncio.Semaphore(self._max_concurrent)
            self._semaphores_by_loop[key] = sem
        return sem

    def _submission_lock_for_loop(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        key = id(loop)
        lock = self._locks_by_loop.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks_by_loop[key] = lock
        return lock

    def _startup_cleanup(self) -> None:
        """Recover only tasks whose V2 worker lease has expired."""
        try:
            self.task_repository.recover_expired_leases()
        except Exception as exc:
            logger.warning("Failed to perform startup task cleanup: %s", exc)

    def _get_pending_tasks_sync(self, limit: int) -> List[Dict[str, Any]]:
        records = self.task_repository.list_tasks(
            project_id=self.project_id,
            statuses={TaskStatus.PENDING},
            limit=limit,
        )
        return [self._task_to_dict(record) for record in reversed(records)]

    async def _run_pending_tasks_loop(self) -> None:
        """Continuously poll for pending tasks and dispatch them if concurrency allows."""
        while True:
            try:
                await asyncio.sleep(2)
                if not self.root_dir.exists():
                    continue

                # Query pending tasks
                pending_tasks = await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._get_pending_tasks_sync,
                    10
                )

                for task in pending_tasks:
                    task_id = task["id"]
                    goal = task["goal"]
                    chapter_id = task.get("chapter_id")
                    dry_run = bool(task.get("dry_run", 0))

                    if task_id in self._running_tasks:
                        continue

                    if not _is_auto_resumable_single_chapter_task(task):
                        continue

                    if chapter_id in self._running_chapters:
                        continue

                    self._running_chapters[chapter_id] = task_id
                    logger.info("Resuming pending chapter task %s for chapter %s", task_id, chapter_id)
                    t = self._create_task(
                        task_id,
                        partial(
                            self._run_chapter,
                            task_id,
                            chapter_id,
                            goal,
                            dry_run,
                        ),
                    )
                    self._running_tasks[task_id] = t

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in pending tasks loop: %s", exc)
                await asyncio.sleep(5)

    def _wrap_store_ws_notify(self) -> None:
        """V2 writes notify from TaskManager helpers, not by monkey-patching the store."""

    @staticmethod
    def _notify_tasks_changed() -> None:
        try:
            from web.task_ws_hub import notify_tasks_changed

            notify_tasks_changed()
        except Exception:
            pass

    def _task_to_dict(self, task: TaskRecord) -> Dict[str, Any]:
        payload = dict(task.payload_json)
        checkpoint = dict(task.checkpoint or {})
        progress = checkpoint.get("progress")
        result = dict(task.result_json or {})
        error = result.pop("_error", None)
        llm_logs = result.pop("_llm_logs", None)
        return {
            "id": task.id,
            "task_id": task.id,
            "project_id": task.project_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "chapter_id": payload.get("chapter_id") or checkpoint.get("chapter_id"),
            "goal": payload.get("goal", ""),
            "mode": payload.get("mode", "standard"),
            "dry_run": bool(payload.get("dry_run", False)),
            "payload": payload,
            "result": result or None,
            "error": error,
            "progress": progress,
            "llm_logs": llm_logs,
            "current_step": checkpoint.get("step")
            or (progress or {}).get("step"),
            "pipeline_version": "V2",
            "updated_at": (
                task.heartbeat_at or task.started_at or task.created_at
            ).isoformat(),
            "last_heartbeat": (
                task.heartbeat_at.isoformat() if task.heartbeat_at else None
            ),
            "resumable_from": checkpoint.get("resumable_from"),
            "status_reason": task.status_reason,
            "created_at": task.created_at.isoformat(),
            "attempt": task.attempt,
            "max_attempts": task.max_attempts,
        }

    def _create_task_record(
        self,
        task_id: str,
        task_type: TaskType,
        payload: Dict[str, Any],
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        record = self.task_repository.create_task(
            task_id=task_id,
            project_id=self.project_id,
            task_type=task_type,
            payload=payload,
            max_attempts=max_attempts,
        )
        self._notify_tasks_changed()
        return self._task_to_dict(record)

    def _update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        llm_logs: Optional[List[Dict[str, Any]]] = None,
        status_reason: Optional[str] = None,
        resumable_from: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status == "completed":
            normalized = TaskStatus.SUCCEEDED
        elif status == "aborted":
            normalized = TaskStatus.CANCELLED
        else:
            normalized = TaskStatus(status)
        current = self.task_repository.get_task(task_id)
        if current is None:
            raise KeyError(f"Task {task_id!r} not found")
        if normalized is TaskStatus.RUNNING:
            if current.status is TaskStatus.PENDING:
                current = self.task_repository.claim_task(task_id)
                if current is None:
                    raise RuntimeError(f"Task {task_id!r} could not be claimed")
            if current.status is TaskStatus.CLAIMED:
                self._claim_tokens[task_id] = current.claim_token or ""
                current = self.task_repository.start_task(
                    task_id,
                    current.claim_token or "",
                )
            self._notify_tasks_changed()
            return self._task_to_dict(current)
        if current.status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
            return self._task_to_dict(current)
        if normalized is TaskStatus.CANCELLED:
            reason = status_reason or error or "user_cancelled"
            for _ in range(3):
                current = self.task_repository.get_task(task_id)
                if current is None:
                    raise KeyError(f"Task {task_id!r} not found")
                if current.status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
                    break
                try:
                    current = self.task_repository.cancel_task(
                        task_id,
                        reason=reason,
                    )
                    break
                except TaskConflictError:
                    continue
            else:
                raise RuntimeError(f"Task {task_id!r} changed repeatedly during cancellation")
        else:
            token = self._claim_tokens.get(task_id) or current.claim_token
            if current.status is TaskStatus.PENDING:
                claimed = self.task_repository.claim_task(task_id)
                if claimed is None:
                    raise RuntimeError(f"Task {task_id!r} could not be claimed")
                token = claimed.claim_token
                current = self.task_repository.start_task(task_id, token or "")
                self._claim_tokens[task_id] = token or ""
            payload = dict(result or {})
            if error:
                payload["_error"] = error
            if llm_logs:
                payload["_llm_logs"] = llm_logs
            if resumable_from:
                existing_checkpoint = dict(current.checkpoint or {})
                existing_checkpoint["resumable_from"] = resumable_from
                current = self.task_repository.heartbeat(
                    task_id,
                    token or "",
                    checkpoint=existing_checkpoint,
                )
            current = self.task_repository.finish_task(
                task_id,
                token or "",
                status=normalized,
                result=payload or None,
                reason=status_reason or error,
            )
        self._claim_tokens.pop(task_id, None)
        self._notify_tasks_changed()
        return self._task_to_dict(current)

    def _update_task_progress(self, task_id: str, progress: Dict[str, Any]) -> None:
        token = self._claim_tokens.get(task_id)
        if not token:
            return
        current = self.task_repository.get_task(task_id)
        checkpoint = dict(current.checkpoint or {}) if current else {}
        checkpoint.update({"progress": progress, "step": progress.get("step")})
        self.task_repository.heartbeat(
            task_id,
            token,
            checkpoint=checkpoint,
        )
        self._notify_tasks_changed()

    def _update_task_chapter_id(self, task_id: str, chapter_id: str) -> None:
        token = self._claim_tokens.get(task_id)
        if not token:
            return
        current = self.task_repository.get_task(task_id)
        checkpoint = dict(current.checkpoint or {}) if current else {}
        checkpoint["chapter_id"] = chapter_id
        self.task_repository.heartbeat(task_id, token, checkpoint=checkpoint)
        self._notify_tasks_changed()

    async def _ensure_llm_ready(self, dry_run: bool) -> None:
        if dry_run:
            return
        await asyncio.get_running_loop().run_in_executor(
            None, assert_llm_ready, self.root_dir
        )

    async def _mark_task_failed(
        self,
        task_id: str,
        exc: BaseException,
        *,
        resumable_from: Optional[str] = None,
    ) -> None:
        from web.task_failures import task_failure_error_string, task_failure_result

        payload = task_failure_result(exc, resumable_from=resumable_from)
        await asyncio.get_running_loop().run_in_executor(
            None,
            self._update_task_status,
            task_id,
            "failed",
            payload,
            task_failure_error_string(exc),
        )

    def _on_progress_emitted(self, msg: Dict[str, Any]) -> None:
        handle_progress_message(
            msg,
            root_exists=self.root_dir.exists,
            update_task_progress=self._update_task_progress,
            update_task_chapter_id=self._update_task_chapter_id,
        )

    async def submit_chapter(
        self,
        chapter_id: str,
        goal: str,
        dry_run: bool = False,
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        
        async with self._submission_lock_for_loop():
            # Check and reserve the chapter atomically across concurrent requests.
            is_running = False
            if chapter_id in self._running_chapters:
                is_running = True
            else:
                task_data = await asyncio.get_running_loop().run_in_executor(
                    None, self._get_active_chapter_tasks, chapter_id
                )
                if task_data:
                    is_running = True

            if is_running:
                raise ValueError(f"Chapter {chapter_id} is already running")

            await asyncio.get_running_loop().run_in_executor(
                None,
                self._create_task_record,
                task_id,
                TaskType.CHAPTER,
                {
                    "chapter_id": chapter_id,
                    "goal": goal,
                    "dry_run": dry_run,
                    "mode": "standard",
                },
            )
            await asyncio.get_running_loop().run_in_executor(
                None,
                partial(self.task_repository.delete_old_tasks, keep=50),
            )
            self._running_chapters[chapter_id] = task_id
        
        task = self._create_task(
            task_id,
            partial(self._run_chapter, task_id, chapter_id, goal, dry_run),
        )
        self._running_tasks[task_id] = task
        return task_id

    async def submit_chapter_gate_only(self, chapter_id: str) -> str:
        task_id = str(uuid.uuid4())[:8]
        goal = f"gate_only:{chapter_id}"

        async with self._submission_lock_for_loop():
            if chapter_id in self._running_chapters:
                raise ValueError(f"Chapter {chapter_id} is already running")
            task_data = await asyncio.get_running_loop().run_in_executor(
                None, self._get_active_chapter_tasks, chapter_id
            )
            if task_data:
                raise ValueError(f"Chapter {chapter_id} is already running")

            await asyncio.get_running_loop().run_in_executor(
                None,
                self._create_task_record,
                task_id,
                TaskType.CHAPTER,
                {
                    "chapter_id": chapter_id,
                    "goal": goal,
                    "dry_run": False,
                    "mode": "gate_only",
                },
            )
            self._running_chapters[chapter_id] = task_id

        task = self._create_task(
            task_id,
            partial(self._run_chapter_gate_only, task_id, chapter_id),
        )
        self._running_tasks[task_id] = task
        return task_id

    async def _run_chapter_gate_only(self, task_id: str, chapter_id: str) -> None:
        token = task_id_var.set(task_id)
        try:
            await asyncio.wait_for(self._semaphore_for_loop().acquire(), timeout=600)
        except asyncio.TimeoutError:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "failed",
                None,
                "Too many concurrent tasks. Please wait and retry.",
            )
            self._running_chapters.pop(chapter_id, None)
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)
            return

        await asyncio.get_running_loop().run_in_executor(
            None, self._update_task_status, task_id, "running"
        )
        try:
            await self._ensure_llm_ready(False)
            config = PipelineConfig.from_config(self.root_dir)
            orchestrator = NovelOrchestrator(config)
            result = await orchestrator.arun_gate_only(chapter_id)
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "completed",
                {
                    "chapter_id": result.chapter_id,
                    "final_path": str(result.final_path),
                    "gate_only": True,
                    "warnings": getattr(result, "warnings", []),
                },
                None,
                config.get_call_log(),
            )
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._sync_task_chapter_version,
                chapter_id,
                str(result.final_path),
            )
        except Exception as exc:
            logger.exception("Gate-only task %s failed", task_id)
            await self._mark_task_failed(task_id, exc)
        finally:
            self._semaphore_for_loop().release()
            self._running_chapters.pop(chapter_id, None)
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)

    def _get_active_chapter_tasks(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous query helper run in executor."""
        active = self.task_repository.list_tasks(
            project_id=self.project_id,
            statuses={
                TaskStatus.PENDING,
                TaskStatus.CLAIMED,
                TaskStatus.RUNNING,
                TaskStatus.PAUSED,
            },
            limit=500,
        )
        for record in active:
            if str(record.payload_json.get("chapter_id") or "") == chapter_id:
                return self._task_to_dict(record)
        return None

    def is_aborted(self, task_id: str) -> bool:
        return task_id in self._aborted_tasks

    async def abort_task(self, task_id: str) -> bool:
        # Check DB status
        task_data = await asyncio.get_running_loop().run_in_executor(
            None, self.get_task, task_id
        )
        if not task_data:
            return False
        if task_data["status"] in ("succeeded", "failed", "cancelled"):
            return False
            
        self._aborted_tasks.add(task_id)
        
        async_task = self._running_tasks.pop(task_id, None)
        if async_task and not async_task.done():
            async_task.cancel()
            
        chapter_id = task_data.get("chapter_id")
        if chapter_id:
            self._running_chapters.pop(chapter_id, None)
            
        await asyncio.get_running_loop().run_in_executor(
            None,
            self._update_task_status,
            task_id,
            "cancelled",
            None,
            "Task aborted by user",
            None,
            "user_abort",
            task_data.get("current_step") or "unknown",
        )
        return True

    def _sync_task_chapter_version(self, chapter_id: str, final_path: str) -> None:
        try:
            p = Path(final_path)
            if p.exists():
                content = p.read_text(encoding="utf-8")
                plan_path = p.parent / "plan.json"
                plan_str = "{}"
                if plan_path.exists():
                    try:
                        plan_str = plan_path.read_text(encoding="utf-8")
                    except Exception:
                        pass
                
                versions = self.store.list_chapter_versions(chapter_id)
                active_version = next((v for v in versions if v.get("is_active") == 1), None)
                if active_version:
                    self.store.save_chapter_version(
                        chapter_id=chapter_id,
                        version_name=active_version["version_name"],
                        content=content,
                        plan=active_version.get("plan") or plan_str,
                        is_active=True,
                        note=active_version.get("note", "") or "AI 写作自动同步",
                        version_id=active_version["id"]
                    )
                else:
                    self.store.save_chapter_version(
                        chapter_id=chapter_id,
                        version_name="版本 A",
                        content=content,
                        plan=plan_str,
                        is_active=True,
                        note="AI 写作自动同步"
                    )
        except Exception as exc:
            logger.warning("Failed to sync AI chapter content to version DB: %s", exc)

    async def get_task_async(self, task_id: str) -> Optional[Dict[str, Any]]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.get_task, task_id
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous get_task for backward compatibility / tests."""
        task = self.task_repository.get_task(task_id)
        return self._task_to_dict(task) if task else None

    async def list_tasks_async(self) -> List[Dict[str, Any]]:
        return await asyncio.get_running_loop().run_in_executor(
            None, self.list_tasks
        )

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Synchronous list_tasks for legacy compatibility."""
        return [
            self._task_to_dict(task)
            for task in self.task_repository.list_tasks(
                project_id=self.project_id,
                limit=50,
            )
        ]

    def has_active_tasks(self) -> bool:
        for task in self._running_tasks.values():
            try:
                if task.done() is True:
                    continue
            except Exception:
                pass
            return True
        return bool(
            self.task_repository.list_tasks(
                project_id=self.project_id,
                statuses={
                    TaskStatus.PENDING,
                    TaskStatus.CLAIMED,
                    TaskStatus.RUNNING,
                    TaskStatus.PAUSED,
                },
                limit=1,
            )
        )

    def sync_concurrency_limit(self) -> int:
        """Reload max concurrent chapters from pipeline; clears per-loop semaphores."""
        from novel_agent.services.execution_policy import resolve_max_concurrent_chapters

        new_limit = resolve_max_concurrent_chapters(self.root_dir)
        if new_limit != self._max_concurrent:
            self._max_concurrent = new_limit
            self._semaphores_by_loop.clear()
        return self._max_concurrent

    def get_queue_snapshot(self) -> Dict[str, Any]:
        from web.tasks_autopilot import active_novel_batch_task_id_helper

        active_count = sum(
            1 for task in self._running_tasks.values() if not task.done()
        )
        return {
            "max_concurrent_chapters": self._max_concurrent,
            "active_task_count": active_count,
            "running_chapters": sorted(self._running_chapters.keys()),
            "novel_batch_task_id": active_novel_batch_task_id_helper(self),
        }

    async def submit_batch(
        self,
        chapters: list,
        dry_run: bool = False,
    ) -> str:
        batch_id = str(uuid.uuid4())[:8]
        await asyncio.get_running_loop().run_in_executor(
            None,
            self._create_task_record,
            batch_id,
            TaskType.CHAPTER_BATCH,
            {
                "chapters": chapters,
                "goal": f"批量生成 {len(chapters)} 章",
                "dry_run": dry_run,
            },
        )
        task = self._create_task(
            batch_id,
            partial(self._run_batch, batch_id, chapters, dry_run),
        )
        self._running_tasks[batch_id] = task
        return batch_id

    async def _run_batch(self, batch_id: str, chapters: list, dry_run: bool) -> None:
        token = task_id_var.set(batch_id)
        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                batch_id,
                "running",
            )
            await run_chapter_batch(
                batch_id,
                chapters,
                dry_run,
                submit_chapter=self.submit_chapter,
                get_task_async=self.get_task_async,
                is_aborted=self.is_aborted,
                running_tasks=self._running_tasks,
            )
            if self.is_aborted(batch_id):
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._update_task_status,
                    batch_id,
                    "cancelled",
                    None,
                    "Task aborted",
                    None,
                    "user_abort",
                    "unknown",
                )
            else:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._update_task_status,
                    batch_id,
                    "completed",
                    {"chapter_count": len(chapters)},
                    None,
                )
        except asyncio.CancelledError:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                batch_id,
                "cancelled",
                None,
                "Task aborted",
                None,
                "user_abort",
                "unknown",
            )
            raise
        except Exception as exc:
            logger.exception("Batch task %s failed", batch_id)
            await self._mark_task_failed(batch_id, exc)
        finally:
            self._running_tasks.pop(batch_id, None)
            task_id_var.reset(token)

    async def _run_chapter(
        self,
        task_id: str,
        chapter_id: str,
        goal: str,
        dry_run: bool,
    ) -> None:
        token = task_id_var.set(task_id)
        
        # Concurrency semaphore acquisition
        try:
            await asyncio.wait_for(self._semaphore_for_loop().acquire(), timeout=600)
        except asyncio.TimeoutError:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "failed",
                None,
                "Too many concurrent tasks. Please wait and retry."
            )
            self._running_chapters.pop(chapter_id, None)
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)
            return

        await asyncio.get_running_loop().run_in_executor(
            None,
            self._update_task_status,
            task_id,
            "running"
        )
        logger.info("Task %s started", task_id)

        config = None
        try:
            await self._ensure_llm_ready(dry_run)
            if dry_run:
                config = PipelineConfig.dry_run(self.root_dir)
            else:
                config = PipelineConfig.from_config(self.root_dir)

            orchestrator = NovelOrchestrator(config)
            
            if hasattr(orchestrator, "arun_chapter"):
                result = await orchestrator.arun_chapter(chapter_id, goal)
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, orchestrator.run_chapter, chapter_id, goal)

            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "completed",
                {
                    "chapter_id": result.chapter_id,
                    "final_path": str(result.final_path),
                    "risk_level": result.audit.get("risk_level", ""),
                    "warnings": getattr(result, "warnings", []),
                },
                None,
                config.get_call_log()
            )
            
            # Sync generated content to version DB
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._sync_task_chapter_version,
                chapter_id,
                str(result.final_path)
            )
        except asyncio.CancelledError:
            logger.info("Task %s cancelled", task_id)
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "cancelled",
                None,
                "已中止"
            )
        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc)
            await self._mark_task_failed(task_id, exc)
        finally:
            if config is not None:
                try:
                    await config.close_llm_clients()
                except Exception as exc:
                    logger.warning("Failed to close LLM clients for task %s: %s", task_id, exc)
            self._semaphore_for_loop().release()
            self._running_chapters.pop(chapter_id, None)
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)

    async def submit_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
        dry_run: bool = False,
    ) -> str:
        task_id = f"novel-{str(uuid.uuid4())[:8]}"
        await asyncio.get_running_loop().run_in_executor(
            None,
            self._create_task_record,
            task_id,
            TaskType.NOVEL_RUN,
            {
                "theme": theme,
                "genre": genre,
                "target_chapters": target_chapters,
                "special_requirements": special_requirements,
                "goal": f"全书生成：{theme}",
                "dry_run": dry_run,
            },
        )
        await asyncio.get_running_loop().run_in_executor(
            None,
            partial(self.task_repository.delete_old_tasks, keep=50),
        )
        
        task = self._create_task(
            task_id,
            partial(
                self._run_novel,
                task_id,
                theme,
                genre,
                target_chapters,
                special_requirements,
                dry_run,
            ),
        )
        self._running_tasks[task_id] = task
        return task_id

    async def submit_arc_run(
        self,
        arc_id: str = "",
        arc_ids: Optional[List[str]] = None,
        start_arc_id: str = "",
        resume: bool = True,
        max_chapters: int = 0,
        dry_run: bool = False,
    ) -> str:
        task_id = f"arc-{str(uuid.uuid4())[:8]}"
        label = arc_id or start_arc_id or ",".join(arc_ids or []) or "arcs"
        await asyncio.get_running_loop().run_in_executor(
            None,
            self._create_task_record,
            task_id,
            TaskType.ARC_RUN,
            {
                "arc_id": arc_id,
                "arc_ids": arc_ids or [],
                "start_arc_id": start_arc_id,
                "resume": resume,
                "max_chapters": max_chapters,
                "goal": f"故事弧批量：{label}",
                "dry_run": dry_run,
            },
        )
        task = self._create_task(
            task_id,
            partial(
                self._run_arc_batch,
                task_id, arc_id, arc_ids or [], start_arc_id, resume, max_chapters, dry_run
            ),
        )
        self._running_tasks[task_id] = task
        return task_id

    async def submit_novel_continue(
        self,
        resume: bool = True,
        max_chapters: int = 0,
        dry_run: bool = False,
        *,
        autopilot: bool = False,
        full_book: bool = True,
        chapters_per_round: int = 0,
        max_rounds: int = 0,
    ) -> str:
        helper = _get_autopilot_helper()
        return await helper(
            self,
            resume,
            max_chapters,
            dry_run,
            autopilot=autopilot,
            full_book=full_book,
            chapters_per_round=chapters_per_round,
            max_rounds=max_rounds,
        )


    async def _run_arc_batch(
        self,
        task_id: str,
        arc_id: str,
        arc_ids: List[str],
        start_arc_id: str,
        resume: bool,
        max_chapters: int,
        dry_run: bool,
    ) -> None:
        token = task_id_var.set(task_id)
        try:
            await asyncio.wait_for(self._semaphore_for_loop().acquire(), timeout=600)
        except asyncio.TimeoutError:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "failed",
                None,
                "Too many concurrent tasks.",
            )
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)
            return

        await asyncio.get_running_loop().run_in_executor(
            None, self._update_task_status, task_id, "running"
        )
        try:
            await self._ensure_llm_ready(dry_run)
            config = PipelineConfig.dry_run(self.root_dir) if dry_run else PipelineConfig.from_config(self.root_dir)
            orchestrator = NovelOrchestrator(config)
            cap = int(max_chapters) if max_chapters and max_chapters > 0 else None
            results = await orchestrator.arun_arcs(
                arc_id=arc_id or None,
                arc_ids=arc_ids or None,
                start_arc_id=start_arc_id or None,
                resume=resume,
                max_chapters=cap,
            )
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "completed",
                {
                    "chapters_completed": len(results),
                    "chapters": [
                        {"chapter_id": r.chapter_id, "warnings": getattr(r, "warnings", [])}
                        for r in results
                    ],
                },
            )
        except Exception as exc:
            logger.exception("Arc batch task %s failed: %s", task_id, exc)
            await self._mark_task_failed(task_id, exc)
        finally:
            self._semaphore_for_loop().release()
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)



    async def _run_novel(
        self,
        task_id: str,
        theme: str,
        genre: str,
        target_chapters: int,
        special_requirements: str,
        dry_run: bool,
    ) -> None:
        token = task_id_var.set(task_id)
        
        try:
            await asyncio.wait_for(self._semaphore_for_loop().acquire(), timeout=600)
        except asyncio.TimeoutError:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "failed",
                None,
                "Too many concurrent tasks."
            )
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)
            return

        await asyncio.get_running_loop().run_in_executor(
            None,
            self._update_task_status,
            task_id,
            "running"
        )

        config = None
        try:
            await self._ensure_llm_ready(dry_run)
            if dry_run:
                config = PipelineConfig.dry_run(self.root_dir)
            else:
                config = PipelineConfig.from_config(self.root_dir)

            orchestrator = NovelOrchestrator(config)
            
            if hasattr(orchestrator, "arun_novel"):
                results = await orchestrator.arun_novel(
                    theme=theme,
                    genre=genre,
                    target_chapters=target_chapters,
                    special_requirements=special_requirements,
                )
            else:
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(
                    None,
                    orchestrator.run_novel,
                    theme,
                    genre,
                    target_chapters,
                    special_requirements
                )

            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "completed",
                {
                    "chapters_completed": len(results),
                    "chapters_requested": target_chapters,
                    "chapters": [
                        {
                            "chapter_id": r.chapter_id,
                            "risk_level": r.audit.get("risk_level", ""),
                            "warnings": getattr(r, "warnings", []),
                        }
                        for r in results
                    ],
                },
                None,
                config.get_call_log()
            )
        except asyncio.CancelledError:
            logger.info("Novel task %s cancelled", task_id)
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._update_task_status,
                task_id,
                "cancelled",
                None,
                "已中止"
            )
        except Exception as exc:
            logger.error("Novel task %s failed: %s", task_id, exc)
            await self._mark_task_failed(task_id, exc)
        finally:
            if config is not None:
                try:
                    await config.close_llm_clients()
                except Exception as exc:
                    logger.warning("Failed to close LLM clients for novel task %s: %s", task_id, exc)
            self._semaphore_for_loop().release()
            self._running_tasks.pop(task_id, None)
            task_id_var.reset(token)
