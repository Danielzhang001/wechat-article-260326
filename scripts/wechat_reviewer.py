#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a deterministic reviewer report for WeChat article publishing.

This is not a style critic. It exists to replace the fragile "handwritten pass.json"
step with a reproducible gate artifact that the pipeline can trust.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


PASS_STATUSES = {"pass", "passed", "approved", "ok", "green"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def reviewer_passed(report: dict[str, Any]) -> bool:
    status = str(report.get("status", "")).strip().lower()
    return status in PASS_STATUSES


def build_reviewer_report(
    *,
    article_title: str,
    markdown_preflight: dict[str, Any],
    pipeline_report: dict[str, Any],
    reviewer: str = "auto-reviewer",
) -> dict[str, Any]:
    md_hard = list(markdown_preflight.get("hard_issues") or [])
    md_warn = list(markdown_preflight.get("warnings") or [])
    hard = list(pipeline_report.get("hard_issues") or [])
    warn = list(pipeline_report.get("warnings") or [])

    section_count = int(pipeline_report.get("section_count") or 0)
    section_image_count = int(pipeline_report.get("section_image_count") or 0)
    gold_feature_count = int(pipeline_report.get("gold_feature_count") or 0)
    standalone_gold_lines = int(markdown_preflight.get("standalone_gold_lines") or 0)

    blocking_reasons = unique_keep_order(md_hard + hard)
    notes: list[str] = []

    if section_count:
        notes.append(f"正文共 {section_count} 个小节，已生成 {section_image_count} 张配图。")
    notes.append(f"Markdown 金句块 {standalone_gold_lines} 处，HTML 高亮/金句特征 {gold_feature_count} 处。")

    if blocking_reasons:
        status = "fail"
        notes.append("存在硬问题，当前版本不允许上传。")
    else:
        status = "pass"
        notes.append("未发现硬问题，允许进入上传。")

    return {
        "reviewer": reviewer,
        "status": status,
        "checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "article": article_title,
        "blocking_reasons": blocking_reasons,
        "notes": unique_keep_order(notes),
        "non_blocking_warnings": unique_keep_order(md_warn + warn),
        "summary": {
            "section_count": section_count,
            "section_image_count": section_image_count,
            "standalone_gold_lines": standalone_gold_lines,
            "gold_feature_count": gold_feature_count,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate WeChat reviewer report")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--markdown-preflight", required=True, help="Markdown preflight JSON path")
    parser.add_argument("--pipeline-report", required=True, help="Pipeline report JSON path")
    parser.add_argument("--output", required=True, help="Reviewer report output path")
    parser.add_argument("--reviewer", default="auto-reviewer", help="Reviewer name to record")
    args = parser.parse_args()

    md_preflight_path = Path(args.markdown_preflight)
    pipeline_report_path = Path(args.pipeline_report)
    output_path = Path(args.output)

    if not md_preflight_path.exists():
        raise SystemExit(f"Markdown preflight not found: {md_preflight_path}")
    if not pipeline_report_path.exists():
        raise SystemExit(f"Pipeline report not found: {pipeline_report_path}")

    markdown_preflight = load_json(md_preflight_path)
    pipeline_report = load_json(pipeline_report_path)

    report = build_reviewer_report(
        article_title=args.title.strip(),
        markdown_preflight=markdown_preflight,
        pipeline_report=pipeline_report,
        reviewer=args.reviewer.strip() or "auto-reviewer",
    )
    save_json(output_path, report)

    print(f"Reviewer report: {output_path}")
    print(f"Status: {report['status']}")
    return 0 if reviewer_passed(report) else 3


if __name__ == "__main__":
    raise SystemExit(main())
