#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat article quality guard.
- Markdown checks: natural tone, anti-template wording, paragraph/sentence variability.
- HTML checks: breathing layout, image source visibility for WeChat.
- Emotion checks: emotional hook strength, scene lead-in, quote/highlight blocks.
- Hook mode: parse Claude Code hook JSON from stdin and inspect changed files.

This script is non-blocking by default (exit 0). Use --strict to fail on hard issues.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

EMOTION_WORDS = [
    "焦虑", "害怕", "怕", "崩溃", "后悔", "不甘", "迷茫", "委屈", "压力", "扛不住",
    "自责", "羞耻", "尴尬", "慌", "痛苦", "失望", "被看见", "翻盘", "救", "希望",
]
SCENE_WORDS = [
    "凌晨", "深夜", "地铁", "工位", "咖啡店", "会议室", "回家路上", "朋友圈", "评论区",
    "那天", "刚刚", "昨晚", "今天早上", "手机", "屏幕", "办公室", "饭桌",
]
RESULT_WORDS = [
    "省下", "涨粉", "变现", "拿到", "跑通", "复购", "成交", "转化", "提升", "完成",
]
RIGID_TITLE_PATTERNS = [
    "全盘点", "从入门到精通", "详解", "大全", "指南", "全面解析", "深度解读",
]


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    # UTF-8 with BOM support.
    return data.decode("utf-8-sig", errors="replace")


def _has_bom(path: Path) -> bool:
    return path.read_bytes().startswith(b"\xef\xbb\xbf")


def _remove_bom(path: Path) -> bool:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(raw[3:])
        return True
    return False


def _parse_float_from_style(style: str, prop: str) -> float | None:
    m = re.search(rf"{re.escape(prop)}\s*:\s*([0-9]+(?:\.[0-9]+)?)", style, re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _sentences(text: str) -> List[str]:
    parts = re.split(r"[。！？!?]\s*", text)
    return [p.strip() for p in parts if p.strip()]


def _paragraphs_md(text: str) -> List[str]:
    blocks = re.split(r"\n\s*\n", text)
    out = []
    for b in blocks:
        s = b.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        out.append(s)
    return out


def _strip_tags(text: str) -> str:
    s = re.sub(r"<script\b[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    s = re.sub(r"<style\b[^>]*>.*?</style>", "", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def _count_any(text: str, words: List[str]) -> int:
    return sum(text.count(w) for w in words)


def _first_meaningful_text_md(text: str, max_chars: int = 260) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    joined = " ".join(lines)
    return joined[:max_chars]


def _title_from_markdown(text: str) -> str:
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return ""


def check_title_hook(title: str) -> Tuple[List[str], List[str], Dict[str, int]]:
    hard: List[str] = []
    warn: List[str] = []
    title = (title or "").strip()
    if not title:
        return hard, warn, {"title_bytes": 0, "emotion_hits": 0, "scene_hits": 0, "result_hits": 0}

    t_bytes = len(title.encode("utf-8"))
    if t_bytes > 64:
        hard.append("标题超过微信64字节限制。")

    # Prefer conflict/emotion + scene/result structure.
    emotion_hits = _count_any(title, EMOTION_WORDS)
    scene_hits = _count_any(title, SCENE_WORDS)
    result_hits = _count_any(title, RESULT_WORDS)
    if emotion_hits == 0 and scene_hits == 0:
        warn.append("标题情绪/场景钩子偏弱，建议加入真实场景或冲突词。")
    if result_hits == 0:
        warn.append("标题结果承诺不明确，建议加入可兑现结果词（省下/跑通/拿到）。")

    for pat in RIGID_TITLE_PATTERNS:
        if pat in title:
            warn.append(f"标题偏功能导向（含“{pat}”），传播力可能偏弱。")
            break

    # Length sweet spot for mobile preview.
    visible_len = len(title)
    if visible_len < 10 or visible_len > 34:
        warn.append("标题可读长度建议10-34字（当前可能过短/过长）。")

    stats = {
        "title_bytes": t_bytes,
        "emotion_hits": emotion_hits,
        "scene_hits": scene_hits,
        "result_hits": result_hits,
    }
    return hard, warn, stats


def check_cover_text(cover_text: str) -> Tuple[List[str], List[str], Dict[str, int]]:
    hard: List[str] = []
    warn: List[str] = []
    text = (cover_text or "").strip()
    if not text:
        return hard, warn, {"cover_chars": 0, "emotion_hits": 0}

    chars = len(text)
    if chars < 8 or chars > 20:
        warn.append("封面主文案建议8-20字，便于手机端快速识别。")
    emotion_hits = _count_any(text, EMOTION_WORDS)
    if emotion_hits == 0:
        warn.append("封面文案缺少情绪动词，建议加入怕/焦虑/翻盘/扛住等词。")

    return hard, warn, {"cover_chars": chars, "emotion_hits": emotion_hits}


def check_markdown(text: str, require_emotion_map: bool = False) -> Tuple[List[str], List[str], Dict[str, int]]:
    hard: List[str] = []
    warn: List[str] = []

    # Template / robotic connectors.
    rigid_connectors = ["首先", "其次", "再次", "最后", "综上", "总而言之", "值得注意的是"]
    connector_hits = sum(text.count(w) for w in rigid_connectors)
    if connector_hits >= 3:
        warn.append("连接词偏说明书化（首先/其次/综上）出现较多，建议改成口语过渡。")

    # Corporate jargon often makes text sound generated.
    jargon = ["赋能", "闭环", "抓手", "顶层设计", "认知维度", "对齐", "范式", "协同", "生态"]
    jargon_hits = [w for w in jargon if w in text]
    if jargon_hits:
        warn.append(f"检测到偏术语化词汇：{', '.join(jargon_hits[:6])}，建议替换成生活化表达。")

    # First-person presence.
    first_person_hits = text.count("我")
    if first_person_hits < 8:
        warn.append("第一人称痕迹偏少，建议增加真实经历与主观感受。")

    # Bullet-list overuse for article body.
    bullet_lines = len(re.findall(r"(?m)^\s*(?:[-*]|\d+\.)\s+", text))
    if bullet_lines >= 6:
        warn.append("分点列表较多，建议改为叙事段落以提升聊天感。")

    # Sentence variability.
    sent = _sentences(text)
    sent_lengths = [len(s) for s in sent]
    if len(sent_lengths) >= 8:
        try:
            stdev = statistics.pstdev(sent_lengths)
            if stdev < 8:
                warn.append("句长变化偏小，读起来容易机械；建议穿插短句和停顿句。")
        except Exception:
            pass

    # Paragraph breathing.
    paras = _paragraphs_md(text)
    para_lengths = [len(p) for p in paras]
    if len(para_lengths) >= 5:
        long_para = sum(1 for n in para_lengths if n > 280)
        if long_para >= 2:
            warn.append("存在较长段落，建议拆段增强呼吸感。")

    # Emotion-map requirement.
    emotion_markers = ["情绪定位四问", "核心情绪标签", "情绪钩子关键词", "禁忌"]
    marker_hits = sum(1 for m in emotion_markers if m in text)
    if require_emotion_map and marker_hits < 2:
        hard.append("缺少“情绪定位四问/核心情绪标签”模块，不建议直接发布。")
    elif marker_hits < 2:
        warn.append("建议补充“情绪定位四问”，先定情绪再写正文。")

    # Opening hook quality.
    opening = _first_meaningful_text_md(text, max_chars=260)
    if opening:
        if not _contains_any(opening, SCENE_WORDS):
            warn.append("开头场景感偏弱，建议前200字出现时间/地点/动作。")
        if not _contains_any(opening, EMOTION_WORDS):
            warn.append("开头情绪张力偏弱，建议加入真实压力或冲突词。")

    # Gold lines and highlight hints in markdown.
    strong_md = len(re.findall(r"\*\*[^*]{8,80}\*\*", text))
    if strong_md < 3:
        warn.append("金句偏少，建议至少3条加粗金句用于转发传播。")

    stats = {
        "chars": len(text),
        "paragraphs": len(paras),
        "sentences": len(sent),
        "bullet_lines": bullet_lines,
        "connector_hits": connector_hits,
        "first_person_hits": first_person_hits,
        "emotion_marker_hits": marker_hits,
        "strong_md": strong_md,
    }
    return hard, warn, stats


def check_html(text: str) -> Tuple[List[str], List[str], Dict[str, int]]:
    hard: List[str] = []
    warn: List[str] = []

    img_srcs = re.findall(r"<img\b[^>]*?src=[\"']([^\"']+)[\"']", text, re.I)
    p_styles = re.findall(r"<p\b[^>]*?style=[\"']([^\"']+)[\"']", text, re.I)

    if not img_srcs:
        hard.append("HTML 未检测到正文图片。")
    else:
        unsplash = [u for u in img_srcs if "unsplash.com" in u.lower()]
        local = [u for u in img_srcs if re.match(r"^(?:[A-Za-z]:[\\/]|\.{1,2}[\\/]|/)", u)]
        mmbiz = [u for u in img_srcs if "mmbiz.qpic.cn" in u.lower()]

        if unsplash:
            hard.append("检测到 Unsplash 外链图片，发布前应替换为微信CDN地址。")
        if local and not mmbiz:
            hard.append("图片仍是本地路径，发布前需要上传并替换成 mmbiz.qpic.cn。")
        if len(mmbiz) == 0 and len(img_srcs) > 0:
            warn.append("未检测到微信CDN图链，可能导致公众号正文不显示配图。")

    # Optional style rule: avoid per-image explanation captions like "图解：..."
    if re.search(r">\\s*(?:图解|图示|图：|图:|Figure\\s*:)\\s*[^<]{0,120}<", text, re.I):
        warn.append("检测到配图图解文案；当前风格默认为无图解。")

    # Breathing layout check via paragraph styles.
    lh_values = []
    margin_bottom_hits = 0
    for style in p_styles:
        lh = _parse_float_from_style(style, "line-height")
        if lh is not None:
            lh_values.append(lh)
        if re.search(r"margin(?:-bottom)?\s*:\s*[^;]*?(1[89]|[2-9]\d)px", style, re.I):
            margin_bottom_hits += 1

    if lh_values:
        if max(lh_values) < 1.85:
            warn.append("段落行高偏紧，建议 line-height >= 1.85 提升呼吸感。")
    else:
        warn.append("未检测到段落行高设置，建议显式设置 line-height。")

    if margin_bottom_hits == 0:
        warn.append("段落下边距不足，建议增加段间距。")

    h3_styles = re.findall(r"<h3\b[^>]*?style=[\"']([^\"']+)[\"']", text, re.I)
    if h3_styles:
        loose_heading = any(
            re.search(r"margin\s*:\s*(?:[4-9]\d)px", s, re.I)
            or (
                re.search(r"margin-top\s*:\s*(?:[4-9]\d)px", s, re.I)
                and re.search(r"margin-bottom\s*:\s*(?:1[89]|[2-9]\d)px", s, re.I)
            )
            for s in h3_styles
        )
        if not loose_heading:
            warn.append("小标题上下留白偏小，建议增大 h3 的 margin。")

    body_text = _strip_tags(text)
    opening = body_text[:320]
    if opening:
        if not _contains_any(opening, SCENE_WORDS):
            warn.append("正文开头场景钩子偏弱，建议加入具体时间/地点/动作。")
        if not _contains_any(opening, EMOTION_WORDS):
            warn.append("正文开头情绪张力偏弱，建议加入怕/慌/焦虑等冲突词。")

    # Gold lines and gentle highlights.
    strong_count = len(re.findall(r"<strong\b[^>]*>[^<]{8,120}</strong>", text, re.I))
    quote_like_count = len(re.findall(r"background\s*:\s*#(?:f0fbf4|eaf7f0)", text, re.I))
    if strong_count + quote_like_count < 3:
        warn.append("加粗金句不足，建议至少3处。")

    # Highlight blocks: warm background cards.
    warm_block_patterns = [
        r"background\s*:\s*#fff[0-9a-f]{3,4}",
        r"background\s*:\s*#fef[0-9a-f]{3,4}",
        r"background\s*:\s*#fdf[0-9a-f]{3,4}",
        r"background\s*:\s*#ffe[0-9a-f]{3,4}",
        r"background\s*:\s*#eaf7f0",
        r"background\s*:\s*#f0fbf4",
    ]
    warm_hits = 0
    for pat in warm_block_patterns:
        warm_hits += len(re.findall(pat, text, re.I))
    if warm_hits < 2:
        warn.append("温和背景高亮偏少，建议至少2个重点高亮块。")

    stats = {
        "chars": len(text),
        "images": len(img_srcs),
        "p_styles": len(p_styles),
        "wechat_images": sum(1 for u in img_srcs if "mmbiz.qpic.cn" in u.lower()),
        "strong_tags": strong_count,
        "quote_like_tags": quote_like_count,
        "warm_highlight_hits": warm_hits,
    }
    return hard, warn, stats


def is_wechat_candidate(path: Path) -> bool:
    lower = str(path).lower()
    if path.suffix.lower() not in {".md", ".html", ".htm"}:
        return False
    keywords = ["wechat", "公众号", "article", "draft", "publish"]
    return any(k in lower for k in keywords)


def collect_paths_from_hook(payload: dict) -> List[Path]:
    tool_input = payload.get("tool_input") or {}
    paths: List[Path] = []

    for k in ("file_path", "path", "target_file", "output_file"):
        v = tool_input.get(k)
        if isinstance(v, str) and v.strip():
            paths.append(Path(v.strip()))

    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for e in edits:
            if isinstance(e, dict):
                fp = e.get("file_path") or e.get("path")
                if isinstance(fp, str) and fp.strip():
                    paths.append(Path(fp.strip()))

    # De-dup while preserving order.
    dedup: List[Path] = []
    seen = set()
    for p in paths:
        key = str(p)
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    return dedup


def log_result(lines: List[str]) -> None:
    log_dir = Path.home() / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "wechat_quality_guard.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}]\n")
        for line in lines:
            f.write(line + "\n")
        f.write("\n")


def strip_image_captions_html(text: str) -> Tuple[str, int]:
    """
    Remove caption-like paragraphs under images, e.g. '图解：...'
    """
    patterns = [
        r"<p\\b[^>]*>\\s*(?:图解|图示|图：|图:|Figure\\s*:)[^<]{0,160}</p>",
    ]
    removed = 0
    out = text
    for pat in patterns:
        out, n = re.subn(pat, "", out, flags=re.IGNORECASE)
        removed += n
    return out, removed


def run_checks(
    paths: Iterable[Path],
    strict: bool,
    fix_bom: bool,
    strip_captions: bool,
    require_emotion_map: bool,
    title: str,
    cover_text: str,
) -> int:
    out_lines: List[str] = []
    hard_total = 0

    # Optional title/cover checks (run once per invocation).
    if title.strip():
        th, tw, ts = check_title_hook(title)
        if th or tw:
            out_lines.append("[wechat-guard] 标题钩子检查")
            if th:
                hard_total += len(th)
                for h in th:
                    out_lines.append(f"  HARD: {h}")
            for w in tw:
                out_lines.append(f"  WARN: {w}")
            out_lines.append(f"  STATS: {ts}")
    if cover_text.strip():
        ch, cw, cs = check_cover_text(cover_text)
        if ch or cw:
            out_lines.append("[wechat-guard] 封面文案检查")
            if ch:
                hard_total += len(ch)
                for h in ch:
                    out_lines.append(f"  HARD: {h}")
            for w in cw:
                out_lines.append(f"  WARN: {w}")
            out_lines.append(f"  STATS: {cs}")

    for p in paths:
        if not p.exists() or not p.is_file():
            continue
        if not is_wechat_candidate(p):
            continue

        hard: List[str] = []
        warn: List[str] = []
        stats: Dict[str, int] = {}

        if fix_bom and _has_bom(p):
            _remove_bom(p)
            out_lines.append(f"[wechat-guard] 已移除 BOM: {p}")

        text = _read_text(p)
        if strip_captions and p.suffix.lower() in {".html", ".htm"}:
            new_text, removed = strip_image_captions_html(text)
            if removed > 0:
                p.write_text(new_text, encoding="utf-8")
                text = new_text
                out_lines.append(f"[wechat-guard] 已移除配图图解段落({removed}): {p}")
        if p.suffix.lower() == ".md":
            hard, warn, stats = check_markdown(text, require_emotion_map=require_emotion_map)
            auto_title = _title_from_markdown(text)
            if auto_title:
                th, tw, ts = check_title_hook(auto_title)
                if th or tw:
                    hard.extend(th)
                    warn.extend([f"（标题）{w}" for w in tw])
                    stats.update({f"title_{k}": v for k, v in ts.items()})
        else:
            hard, warn, stats = check_html(text)

        if hard or warn:
            out_lines.append(f"[wechat-guard] 检查文件: {p}")
            if hard:
                hard_total += len(hard)
                for h in hard:
                    out_lines.append(f"  HARD: {h}")
            if warn:
                for w in warn:
                    out_lines.append(f"  WARN: {w}")
            out_lines.append(f"  STATS: {stats}")

    if out_lines:
        print("\n".join(out_lines))
        log_result(out_lines)

    if strict and hard_total > 0:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="WeChat article quality guard")
    parser.add_argument("--mode", choices=["hook", "file"], default="hook")
    parser.add_argument("--file", type=str, default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--fix-bom", action="store_true")
    parser.add_argument("--strip-captions", action="store_true")
    parser.add_argument("--require-emotion-map", action="store_true")
    parser.add_argument("--title", type=str, default="")
    parser.add_argument("--cover-text", type=str, default="")
    args = parser.parse_args()

    if args.mode == "file":
        if not args.file:
            return 0
        return run_checks(
            [Path(args.file)],
            strict=args.strict,
            fix_bom=args.fix_bom,
            strip_captions=args.strip_captions,
            require_emotion_map=args.require_emotion_map,
            title=args.title,
            cover_text=args.cover_text,
        )

    # Hook mode
    raw = sys.stdin.read()
    # Some Windows pipelines prepend BOM/mojibake bytes before JSON.
    raw = raw.lstrip("\ufeff").strip()
    if not raw:
        return 0
    paths: List[Path] = []
    try:
        payload = json.loads(raw)
        paths = collect_paths_from_hook(payload)
    except Exception:
        # Fallback for mojibake/partial JSON in Windows pipelines.
        candidates = re.findall(
            r"([A-Za-z]:[\\\\/][^\\r\\n\"']+\\.(?:md|html?))",
            raw,
            flags=re.IGNORECASE,
        )
        if not candidates:
            # Fallback 2: extract from `file_path` fields even in broken JSON.
            candidates = re.findall(
                r'"?file_path"?\s*:\s*"([^"\r\n]+?\.(?:md|html?))"',
                raw,
                flags=re.IGNORECASE,
            )
        for c in candidates:
            paths.append(Path(c.replace("\\\\", "\\")))

    if not paths:
        return 0
    return run_checks(
        paths,
        strict=args.strict,
        fix_bom=args.fix_bom,
        strip_captions=args.strip_captions,
        require_emotion_map=args.require_emotion_map,
        title=args.title,
        cover_text=args.cover_text,
    )


if __name__ == "__main__":
    raise SystemExit(main())
