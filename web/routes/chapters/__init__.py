"""Chapter-related HTTP routes (split by concern)."""

from fastapi import APIRouter

from web.routes.chapters import crud, extras, snapshots, state_candidates, tasks, versions
from web.routes.chapters import chat as chat_routes

router = APIRouter()
for module in (tasks, crud, snapshots, state_candidates, versions, extras, chat_routes):
    router.include_router(module.router)

rewrite_chapter = tasks.rewrite_chapter
resume_chapter_audit = tasks.resume_chapter_audit
get_chapter = crud.get_chapter
list_chapters = crud.list_chapters
suggest_chapter_goal = tasks.suggest_chapter_goal
