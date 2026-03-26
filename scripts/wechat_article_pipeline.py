#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified WeChat article pipeline.

Deterministic responsibilities handled here:
1. Markdown -> WeChat HTML conversion
2. One image per section (h3) via Unsplash + WeChat uploadimg
3. Preflight quality gate before upload/update
4. Draft update or publish
5. Structured error report, including IP whitelist guidance
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import DATA_DIR
from md_to_html import markdown_to_html
from unsplash_image_fetcher import UnsplashImageFetcher
from wechat_publisher import WeChatPublisher
from wechat_quality_guard import check_html, check_markdown, check_title_hook
from wechat_reviewer import build_reviewer_report, reviewer_passed

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = DATA_DIR / "output"
PIPELINE_IMAGES_DIR = DATA_DIR / "images" / "pipeline"

SECTION_QUERY_RULES = [
    (("通勤", "地铁", "上班", "迟到", "大城市", "打工"), "morning subway commute city"),
    (("深渊", "困住", "命运", "出口", "生路", "希望"), "woman by window hope documentary"),
    (("AI", "工具", "PPT", "资料", "效率", "思考"), "artificial intelligence laptop workspace"),
    (("腾地方", "时间", "副业", "学习", "判断", "余力"), "focused desk learning at night"),
    (("选择", "有得选", "路口", "方向", "以后", "人生"), "road fork sunrise freedom"),
]


def setup_utf8() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def first_non_title_paragraph(markdown: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", markdown) if b.strip()]
    for block in blocks:
        if block.startswith("# "):
            continue
        return re.sub(r"\s+", " ", block)
    return ""


def title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def digest_from_markdown(markdown: str, limit: int = 110) -> str:
    text = first_non_title_paragraph(markdown)
    if not text:
        return ""
    return text[:limit]


def infer_query(heading_text: str, paragraph_text: str, article_title: str) -> str:
    heading_lower = heading_text.lower()
    paragraph_lower = paragraph_text.lower()
    title_lower = article_title.lower()

    best_query = "editorial workspace"
    best_score = 0

    for keys, query in SECTION_QUERY_RULES:
        score = 0
        for key in keys:
            key_lower = key.lower()
            if key_lower in heading_lower:
                score += 3
            if key_lower in paragraph_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_query = query

    if best_score > 0:
        return best_query

    for keys, query in SECTION_QUERY_RULES:
        if any(key.lower() in title_lower for key in keys):
            return query

    return "editorial workspace"


def find_section_text_for_heading(heading) -> str:
    paragraph_texts: list[str] = []
    for sibling in heading.find_next_siblings():
        if sibling.name == "h3":
            break
        if sibling.name == "p":
            text = sibling.get_text(" ", strip=True)
            if text:
                paragraph_texts.append(text)
    return " ".join(paragraph_texts)


def insert_section_images(
    soup: BeautifulSoup,
    article_title: str,
    publisher: WeChatPublisher,
    fetcher: UnsplashImageFetcher,
    image_dir: Path,
) -> list[dict]:
    image_dir.mkdir(parents=True, exist_ok=True)
    used_photo_ids: set[str] = set()
    logs: list[dict] = []

    for idx, heading in enumerate(soup.find_all("h3"), start=1):
        heading_text = heading.get_text(" ", strip=True)
        section_text = find_section_text_for_heading(heading)
        query = infer_query(heading_text, section_text or heading_text, article_title)

        results = fetcher.search_photo(query, orientation="landscape", per_page=8)
        photo = None
        for item in results:
            photo_id = item.get("id")
            if photo_id and photo_id not in used_photo_ids:
                photo = item
                used_photo_ids.add(photo_id)
                break

        if not photo:
            raise RuntimeError(f"Unsplash search failed for section: {heading_text}")

        image_url = photo["urls"].get("small") or photo["urls"].get("regular")
        if not image_url:
            raise RuntimeError(f"No downloadable image URL for section: {heading_text}")

        image_path = image_dir / f"section_{idx:02d}.jpg"
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_path.write_bytes(response.content)

        wechat_url = publisher._upload_image(str(image_path))
        if not wechat_url:
            detail = publisher.get_last_error() or {}
            raise RuntimeError(f"Upload image failed for section {heading_text}: {detail.get('errmsg', 'unknown')}")

        wrapper = soup.new_tag("p")
        wrapper["style"] = "text-align:center;margin:28px 0;"
        img = soup.new_tag("img", src=wechat_url)
        img["alt"] = heading_text
        img["style"] = "width:100%;max-width:720px;border-radius:12px;display:block;margin:0 auto;"
        wrapper.append(img)

        heading.insert_after(wrapper)

        logs.append(
            {
                "section": heading_text,
                "query": query,
                "photo_id": photo["id"],
                "wechat_url": wechat_url,
            }
        )

    return logs


def count_golden_features(html: str) -> int:
    strong_count = len(re.findall(r"<strong\b[^>]*>[^<]{8,120}</strong>", html, re.I))
    quote_block_count = len(
        re.findall(
            r'background:\s*#(?:f0fbf4|eaf7f0);',
            html,
            re.I,
        )
    )
    return strong_count + quote_block_count


def build_report(
    markdown_text: str,
    html_text: str,
    title: str,
    section_image_logs: list[dict],
    min_gold_lines: int,
) -> dict:
    md_hard, md_warn, md_stats = check_markdown(markdown_text, require_emotion_map=False)
    html_hard, html_warn, html_stats = check_html(html_text)
    title_hard, title_warn, title_stats = check_title_hook(title)

    section_count = len(re.findall(r"<h3\b", html_text, re.I))
    wechat_image_count = html_stats.get("wechat_images", 0)
    gold_feature_count = count_golden_features(html_text)

    hard = list(title_hard) + list(md_hard) + list(html_hard)
    warn = list(title_warn) + list(md_warn) + list(html_warn)

    if section_count and wechat_image_count < section_count:
        hard.append(f"正文小节数为 {section_count}，但微信图链仅有 {wechat_image_count} 张，未做到一节一图。")

    if gold_feature_count < min_gold_lines:
        hard.append(f"高亮/金句特征仅检测到 {gold_feature_count} 处，低于最少 {min_gold_lines} 处。")

    return {
        "title": title,
        "hard_issues": hard,
        "warnings": warn,
        "title_stats": title_stats,
        "markdown_stats": md_stats,
        "html_stats": html_stats,
        "section_count": section_count,
        "section_image_count": len(section_image_logs),
        "gold_feature_count": gold_feature_count,
        "images": section_image_logs,
    }


def build_markdown_preflight(markdown_text: str, title: str, min_gold_lines: int) -> dict:
    md_hard, md_warn, md_stats = check_markdown(markdown_text, require_emotion_map=False)
    title_hard, title_warn, title_stats = check_title_hook(title)
    standalone_gold_lines = len(re.findall(r"^\s*\*\*[^*\n]{6,}\*\*\s*$", markdown_text, re.MULTILINE))

    hard = list(title_hard) + list(md_hard)
    warn = list(title_warn) + list(md_warn)
    if standalone_gold_lines < min_gold_lines:
        hard.append(f"Markdown 金句块仅检测到 {standalone_gold_lines} 处，低于最少 {min_gold_lines} 处。")

    return {
        "title": title,
        "hard_issues": hard,
        "warnings": warn,
        "title_stats": title_stats,
        "markdown_stats": md_stats,
        "standalone_gold_lines": standalone_gold_lines,
    }


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def load_review_report(path_str: str) -> dict:
    if not path_str:
        return {}
    path = Path(path_str)
    if not path.exists():
        raise RuntimeError(f"Reviewer report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def auto_review_path(md_path: Path) -> Path:
    return OUTPUT_DIR / f"{md_path.stem}.auto_reviewer.json"


def update_or_publish(
    publisher: WeChatPublisher,
    title: str,
    digest: str,
    html: str,
    media_id: str,
    author: str,
    cover_image: str,
) -> bool:
    current_news = None
    target_media_id = media_id

    if target_media_id:
        data = publisher.batch_get_drafts(offset=0, count=50, no_content=0)
        if data:
            for item in data.get("item", []):
                if item.get("media_id") == target_media_id:
                    current_news = ((item.get("content") or {}).get("news_item") or [{}])[0]
                    break
    else:
        target_media_id, current_news = publisher.find_draft_by_title(title, count=50, no_content=0)

    if current_news and target_media_id:
        article = {
            "title": title,
            "author": author or current_news.get("author") or publisher.config.get_author(),
            "digest": digest,
            "content": html,
            "thumb_media_id": current_news["thumb_media_id"],
            "show_cover_pic": current_news.get("show_cover_pic", 1),
            "need_open_comment": current_news.get("need_open_comment", 1),
            "only_fans_can_comment": current_news.get("only_fans_can_comment", 0),
            "content_source_url": current_news.get("content_source_url", ""),
        }
        return publisher.update_draft(target_media_id, article)

    if not cover_image:
        raise RuntimeError("Publishing new draft requires --cover-image when no existing draft is found.")

    return publisher.publish(
        title=title,
        content=html,
        author=author,
        digest=digest,
        images=[cover_image],
        draft=True,
    )


def main() -> int:
    setup_utf8()

    parser = argparse.ArgumentParser(description="Unified WeChat article pipeline")
    parser.add_argument("markdown", help="Markdown article path")
    parser.add_argument("--mode", choices=["personal", "company"], default="personal")
    parser.add_argument("--title", default="", help="Override article title")
    parser.add_argument("--digest", default="", help="Override article digest")
    parser.add_argument("--author", default="", help="Override author")
    parser.add_argument("--media-id", default="", help="Update an existing draft by media_id")
    parser.add_argument("--cover-image", default="", help="Cover image for new draft publishing")
    parser.add_argument("--min-gold-lines", type=int, default=3)
    parser.add_argument("--review-report", default="", help="Reviewer report JSON path")
    parser.add_argument("--skip-review-gate", action="store_true", help="Allow upload without reviewer pass report")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()

    md_path = Path(args.markdown)
    if not md_path.exists():
        print(f"Markdown not found: {md_path}")
        return 1

    publisher = WeChatPublisher()
    fetcher = UnsplashImageFetcher()
    if not fetcher.access_key:
        print("Unsplash access key missing. Configure data/unsplash_config.json first.")
        return 1

    markdown_text = strip_frontmatter(md_path.read_text(encoding="utf-8"))
    title = args.title.strip() or title_from_markdown(markdown_text)
    digest = args.digest.strip() or digest_from_markdown(markdown_text)
    author = args.author.strip() or publisher.config.get_author()

    if not title:
        print("Title missing. Add a '# 标题' line or pass --title.")
        return 1

    preflight = build_markdown_preflight(markdown_text, title, args.min_gold_lines)
    preflight_path = OUTPUT_DIR / f"{md_path.stem}.markdown_preflight.json"
    save_report(preflight_path, preflight)

    if preflight["hard_issues"]:
        print("Markdown preflight failed. Hard issues:")
        for item in preflight["hard_issues"]:
            print(f"- {item}")
        print(f"Report: {preflight_path}")
        return 2

    html = markdown_to_html(markdown_text, mode=args.mode)
    soup = BeautifulSoup(html, "html.parser")
    image_dir = PIPELINE_IMAGES_DIR / md_path.stem
    section_image_logs = insert_section_images(soup, title, publisher, fetcher, image_dir)
    final_html = str(soup)

    report = build_report(markdown_text, final_html, title, section_image_logs, args.min_gold_lines)
    report_path = OUTPUT_DIR / f"{md_path.stem}.pipeline_report.json"
    save_report(report_path, report)

    if report["hard_issues"]:
        print("Preflight failed. Hard issues:")
        for item in report["hard_issues"]:
            print(f"- {item}")
        print(f"Report: {report_path}")
        return 2

    html_out = OUTPUT_DIR / f"{md_path.stem}.wechat.html"
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(final_html, encoding="utf-8")

    generated_review_path = auto_review_path(md_path)
    review = build_reviewer_report(
        article_title=title,
        markdown_preflight=preflight,
        pipeline_report=report,
        reviewer="auto-reviewer",
    )
    save_report(generated_review_path, review)
    review_path = generated_review_path

    if args.no_upload:
        print(f"Preflight passed. HTML: {html_out}")
        print(f"Report: {report_path}")
        print(f"Reviewer: {review_path}")
        return 0

    if not args.skip_review_gate:
        if args.review_report:
            review = load_review_report(args.review_report)
            review_path = Path(args.review_report)
        if not reviewer_passed(review):
            print("Upload blocked: reviewer report did not pass.")
            print(json.dumps(review, ensure_ascii=False, indent=2))
            print(f"Reviewer: {review_path}")
            return 3

    try:
        success = update_or_publish(
            publisher=publisher,
            title=title,
            digest=digest,
            html=final_html,
            media_id=args.media_id.strip(),
            author=author,
            cover_image=args.cover_image.strip(),
        )
    except Exception as e:
        print(f"Pipeline failed: {e}")
        return 1

    if not success:
        error = publisher.get_last_error() or {}
        print("Upload/update failed.")
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 1

    print(f"Pipeline succeeded. HTML: {html_out}")
    print(f"Report: {report_path}")
    print(f"Reviewer: {review_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
