"""SQLite repository mixin for Human Writing Engine (HWE) persistence."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from novel_agent.human_writing.schemas import HWEIssue, HWEReport
from novel_agent.state.sqlite_schema import db_write_lock, safe_connection


class HWERepositoryMixin:
    """Repository Mixin providing persistence for HWE reports, issues, patches, and preferences."""

    db_path: Path

    @db_write_lock
    def save_hwe_report(
        self,
        report: HWEReport | Dict[str, Any],
        chapter_id: Optional[str] = None,
        document_revision_id: Optional[str] = None,
    ) -> str:
        """Save a scan report and all its associated issues in a single transaction."""
        report_id = str(uuid.uuid4())

        if isinstance(report, HWEReport):
            c_id = chapter_id or report.chapter_id or ""
            rev_id = document_revision_id or report.document_revision_id or ""
            eng_ver = report.engine_version
            rule_ver = report.ruleset_version
            mode = report.mode
            char_count = report.char_count
            overall_score = float(report.scores.overall_score)
            template_risk = float(report.scores.template_risk)
            scores_json = json.dumps(report.scores.model_dump(), ensure_ascii=False)
            by_family_json = json.dumps(report.issue_counts_by_family, ensure_ascii=False)
            by_sev_json = json.dumps(report.issue_counts_by_severity, ensure_ascii=False)
            summary = report.summary
            raw_issues = report.issues
        else:
            c_id = chapter_id or report.get("chapter_id") or ""
            rev_id = document_revision_id or report.get("document_revision_id") or ""
            eng_ver = report.get("engine_version", "1.0.0")
            rule_ver = report.get("ruleset_version", "")
            mode = report.get("mode", "assist")
            char_count = int(report.get("char_count", 0))
            scores = report.get("scores", {})
            overall_score = float(scores.get("overall_score", 100.0))
            template_risk = float(scores.get("template_risk", 0.0))
            scores_json = json.dumps(scores, ensure_ascii=False)
            by_family_json = json.dumps(report.get("issue_counts_by_family", {}), ensure_ascii=False)
            by_sev_json = json.dumps(report.get("issue_counts_by_severity", {}), ensure_ascii=False)
            summary = report.get("summary", "")
            raw_issues = report.get("issues", [])

        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into hwe_reports (
                        id, chapter_id, document_revision_id, engine_version,
                        ruleset_version, mode, char_count, overall_score,
                        template_risk, scores_json, issue_counts_by_family,
                        issue_counts_by_severity, summary
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        c_id,
                        rev_id,
                        eng_ver,
                        rule_ver,
                        mode,
                        char_count,
                        overall_score,
                        template_risk,
                        scores_json,
                        by_family_json,
                        by_sev_json,
                        summary,
                    ),
                )

                for item in raw_issues:
                    issue_id = str(uuid.uuid4())
                    if isinstance(item, HWEIssue):
                        rule_id = item.hwe.rule_id
                        family = item.hwe.family
                        severity = item.severity
                        confidence = float(item.hwe.confidence)
                        start_pos = item.hwe.start
                        end_pos = item.hwe.end
                        matched_text = item.hwe.matched_text
                        why = item.why
                        fix = item.fix
                    elif isinstance(item, dict):
                        hwe_detail = item.get("hwe", {})
                        rule_id = hwe_detail.get("rule_id", item.get("rule_id", ""))
                        family = hwe_detail.get("family", item.get("family", "unknown"))
                        severity = item.get("severity", "medium")
                        confidence = float(hwe_detail.get("confidence", 1.0))
                        start_pos = int(hwe_detail.get("start", item.get("start_pos", 0)))
                        end_pos = int(hwe_detail.get("end", item.get("end_pos", 0)))
                        matched_text = hwe_detail.get("matched_text", item.get("matched_text", ""))
                        why = item.get("why", "")
                        fix = item.get("fix", "")
                    else:
                        continue

                    conn.execute(
                        """
                        insert into hwe_issues (
                            id, report_id, chapter_id, rule_id, family,
                            severity, confidence, start_pos, end_pos,
                            matched_text, why, fix, status
                        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
                        """,
                        (
                            issue_id,
                            report_id,
                            c_id,
                            rule_id,
                            family,
                            severity,
                            confidence,
                            start_pos,
                            end_pos,
                            matched_text,
                            why,
                            fix,
                        ),
                    )

        return report_id

    def get_latest_hwe_report(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest HWE report and all its detected issues for a chapter."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rep_row = conn.execute(
                """
                select id, chapter_id, document_revision_id, engine_version,
                       ruleset_version, mode, char_count, overall_score,
                       template_risk, scores_json, issue_counts_by_family,
                       issue_counts_by_severity, summary, created_at
                from hwe_reports
                where chapter_id = ?
                order by created_at desc
                limit 1
                """,
                (chapter_id,),
            ).fetchone()

            if not rep_row:
                return None

            report_id = rep_row["id"]
            issue_rows = conn.execute(
                """
                select id, report_id, chapter_id, rule_id, family, severity,
                       confidence, start_pos, end_pos, matched_text, why, fix,
                       status, resolution_note, created_at
                from hwe_issues
                where report_id = ?
                order by start_pos asc
                """,
                (report_id,),
            ).fetchall()

            return self._build_report_dict(rep_row, issue_rows)

    def get_hwe_report_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific HWE report by ID."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rep_row = conn.execute(
                """
                select id, chapter_id, document_revision_id, engine_version,
                       ruleset_version, mode, char_count, overall_score,
                       template_risk, scores_json, issue_counts_by_family,
                       issue_counts_by_severity, summary, created_at
                from hwe_reports
                where id = ?
                """,
                (report_id,),
            ).fetchone()

            if not rep_row:
                return None

            issue_rows = conn.execute(
                """
                select id, report_id, chapter_id, rule_id, family, severity,
                       confidence, start_pos, end_pos, matched_text, why, fix,
                       status, resolution_note, created_at
                from hwe_issues
                where report_id = ?
                order by start_pos asc
                """,
                (report_id,),
            ).fetchall()

            return self._build_report_dict(rep_row, issue_rows)

    def list_hwe_reports(
        self,
        chapter_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List historical reports."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if chapter_id:
                rows = conn.execute(
                    """
                    select id, chapter_id, document_revision_id, engine_version,
                           ruleset_version, mode, char_count, overall_score,
                           template_risk, summary, created_at
                    from hwe_reports
                    where chapter_id = ?
                    order by created_at desc
                    limit ? offset ?
                    """,
                    (chapter_id, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    select id, chapter_id, document_revision_id, engine_version,
                           ruleset_version, mode, char_count, overall_score,
                           template_risk, summary, created_at
                    from hwe_reports
                    order by created_at desc
                    limit ? offset ?
                    """,
                    (limit, offset),
                ).fetchall()

            return [dict(r) for r in rows]

    @db_write_lock
    def resolve_hwe_issue(
        self,
        issue_id: str,
        status: str,
        resolution_note: str = "",
    ) -> bool:
        """Update the resolution status of an issue (e.g. resolved, ignored, false_positive)."""
        with safe_connection(self.db_path) as conn:
            with conn:
                cur = conn.execute(
                    """
                    update hwe_issues
                    set status = ?, resolution_note = ?
                    where id = ?
                    """,
                    (status, resolution_note, issue_id),
                )
                return cur.rowcount > 0

    def list_hwe_issues(
        self,
        chapter_id: Optional[str] = None,
        report_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query issues by chapter, report, or status."""
        clauses = []
        params: List[Any] = []
        if chapter_id:
            clauses.append("chapter_id = ?")
            params.append(chapter_id)
        if report_id:
            clauses.append("report_id = ?")
            params.append(report_id)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = (" where " + " and ".join(clauses)) if clauses else ""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                select id, report_id, chapter_id, rule_id, family, severity,
                       confidence, start_pos, end_pos, matched_text, why, fix,
                       status, resolution_note, created_at
                from hwe_issues
                {where}
                order by created_at desc
                """,
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    @db_write_lock
    def save_hwe_patch(self, patch_data: Dict[str, Any]) -> str:
        """Save an applied or proposed patch record."""
        patch_id = patch_data.get("id") or str(uuid.uuid4())
        issues_addressed = patch_data.get("issues_addressed", [])
        if isinstance(issues_addressed, list):
            issues_json = json.dumps(issues_addressed, ensure_ascii=False)
        else:
            issues_json = str(issues_addressed)

        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into hwe_patches (
                        id, report_id, chapter_id, target_start, target_end,
                        original_text, patched_text, issues_addressed, status
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        patch_id,
                        patch_data.get("report_id"),
                        patch_data.get("chapter_id"),
                        int(patch_data.get("target_start", 0)),
                        int(patch_data.get("target_end", 0)),
                        patch_data.get("original_text", ""),
                        patch_data.get("patched_text", ""),
                        issues_json,
                        patch_data.get("status", "applied"),
                    ),
                )
        return patch_id

    def list_hwe_patches(
        self,
        chapter_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List patches, optionally filtered by chapter."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if chapter_id:
                rows = conn.execute(
                    """
                    select id, report_id, chapter_id, target_start, target_end,
                           original_text, patched_text, issues_addressed, status, created_at
                    from hwe_patches
                    where chapter_id = ?
                    order by created_at desc
                    limit ?
                    """,
                    (chapter_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    select id, report_id, chapter_id, target_start, target_end,
                           original_text, patched_text, issues_addressed, status, created_at
                    from hwe_patches
                    order by created_at desc
                    limit ?
                    """,
                    (limit,),
                ).fetchall()

            res = []
            for r in rows:
                d = dict(r)
                try:
                    d["issues_addressed"] = json.loads(d["issues_addressed"])
                except Exception:
                    pass
                res.append(d)
            return res

    @db_write_lock
    def save_hwe_preference(
        self,
        preference_key: str,
        value: Any,
        rule_id: str = "",
        project_id: str = "",
    ) -> None:
        """Save or update an adaptive preference (e.g. suppression, weight, style setting)."""
        pref_id = str(uuid.uuid4())
        value_json = json.dumps(value, ensure_ascii=False)
        with safe_connection(self.db_path) as conn:
            with conn:
                conn.execute(
                    """
                    insert into hwe_preferences (
                        id, project_id, preference_key, rule_id, value_json
                    ) values (?, ?, ?, ?, ?)
                    on conflict(project_id, preference_key, rule_id)
                    do update set value_json = excluded.value_json,
                                  updated_at = current_timestamp
                    """,
                    (pref_id, project_id, preference_key, rule_id, value_json),
                )

    def get_hwe_preferences(
        self,
        project_id: str = "",
        preference_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List preferences for a project."""
        clauses = ["project_id = ?"]
        params: List[Any] = [project_id]
        if preference_key:
            clauses.append("preference_key = ?")
            params.append(preference_key)

        where = " where " + " and ".join(clauses)
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                select id, project_id, preference_key, rule_id, value_json, updated_at
                from hwe_preferences
                {where}
                order by updated_at desc
                """,
                params,
            ).fetchall()

            res = []
            for r in rows:
                d = dict(r)
                try:
                    d["value"] = json.loads(d["value_json"])
                except Exception:
                    d["value"] = d["value_json"]
                res.append(d)
            return res

    def get_hwe_rule_preference(
        self,
        rule_id: str,
        preference_key: str,
        project_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Get preference for a specific rule."""
        with safe_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                select id, project_id, preference_key, rule_id, value_json, updated_at
                from hwe_preferences
                where project_id = ? and preference_key = ? and rule_id = ?
                """,
                (project_id, preference_key, rule_id),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["value"] = json.loads(d["value_json"])
            except Exception:
                d["value"] = d["value_json"]
            return d

    @staticmethod
    def _build_report_dict(rep_row: sqlite3.Row, issue_rows: List[sqlite3.Row]) -> Dict[str, Any]:
        report_data = dict(rep_row)
        try:
            report_data["scores"] = json.loads(report_data["scores_json"])
        except Exception:
            report_data["scores"] = {}
        try:
            report_data["issue_counts_by_family"] = json.loads(report_data["issue_counts_by_family"])
        except Exception:
            report_data["issue_counts_by_family"] = {}
        try:
            report_data["issue_counts_by_severity"] = json.loads(report_data["issue_counts_by_severity"])
        except Exception:
            report_data["issue_counts_by_severity"] = {}

        issues = []
        for i_row in issue_rows:
            i_dict = dict(i_row)
            issues.append(
                {
                    "id": i_dict["id"],
                    "rule_id": i_dict["rule_id"],
                    "family": i_dict["family"],
                    "severity": i_dict["severity"],
                    "confidence": i_dict["confidence"],
                    "start": i_dict["start_pos"],
                    "end": i_dict["end_pos"],
                    "matched_text": i_dict["matched_text"],
                    "why": i_dict["why"],
                    "fix": i_dict["fix"],
                    "status": i_dict["status"],
                    "resolution_note": i_dict["resolution_note"],
                    "created_at": i_dict["created_at"],
                    "hwe": {
                        "rule_id": i_dict["rule_id"],
                        "family": i_dict["family"],
                        "confidence": i_dict["confidence"],
                        "start": i_dict["start_pos"],
                        "end": i_dict["end_pos"],
                        "matched_text": i_dict["matched_text"],
                    },
                }
            )
        report_data["issues"] = issues
        return report_data
