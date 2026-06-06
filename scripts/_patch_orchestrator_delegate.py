from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "novel_agent/orchestrator.py"
src = path.read_text(encoding="utf-8")
start = src.index("    async def _run_chapter_briefs")
end = src.index("    def _auto_compress_assets")
replacement = '''    async def _run_chapter_briefs(
        self,
        chapter_briefs: List[Dict[str, Any]],
        arc_id: str = "",
        calibration_interval: int = 0,
        all_chapters_ref: Optional[List[Dict[str, Any]]] = None,
        global_offset: int = 0,
    ) -> Tuple[List[ChapterResult], bool]:
        return await novel_batch_run_chapter_briefs(
            self,
            chapter_briefs,
            arc_id=arc_id,
            calibration_interval=calibration_interval,
            all_chapters_ref=all_chapters_ref,
            global_offset=global_offset,
        )

    async def arun_arcs(
        self,
        arc_id: Optional[str] = None,
        arc_ids: Optional[List[str]] = None,
        start_arc_id: Optional[str] = None,
        resume: bool = True,
        max_chapters: Optional[int] = None,
    ) -> List[ChapterResult]:
        return await novel_batch_arun_arcs(
            self,
            arc_id=arc_id,
            arc_ids=arc_ids,
            start_arc_id=start_arc_id,
            resume=resume,
            max_chapters=max_chapters,
        )

    async def arun_novel_continue(
        self,
        resume: bool = True,
        max_chapters: Optional[int] = None,
        *,
        full_book: bool = False,
    ) -> List[ChapterResult]:
        return await novel_batch_arun_novel_continue(
            self,
            resume=resume,
            max_chapters=max_chapters,
            full_book=full_book,
        )

    async def arun_novel(
        self,
        theme: str,
        genre: str = "玄幻",
        target_chapters: int = 20,
        special_requirements: str = "",
    ) -> List[ChapterResult]:
        return await novel_batch_arun_novel(
            self,
            theme,
            genre=genre,
            target_chapters=target_chapters,
            special_requirements=special_requirements,
        )

'''
path.write_text(src[:start] + replacement + src[end:], encoding="utf-8")
print("patched orchestrator.py")