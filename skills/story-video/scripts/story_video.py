#!/usr/bin/env python3
"""Validate story-video specifications and prepare a project directory."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]

ASSET_NAMES = ("handdraw.js", "xiaohei.js", "microactions.js", "props.js")
PATTERNS = {
    "character-state",
    "dialogue",
    "journey",
    "process",
    "comparison",
    "cause-effect",
    "reveal",
    "summary",
}
VIEWS = {"front", "side"}
ACTIONS = {"idle", "blink", "wave", "walk", "nod", "jump", "think", "surprise"}
SILENT_FIELDS = {"audio", "bgm", "music", "voiceover", "narration", "sfx"}
ANNOTATION_COLORS = {"#e2483d", "#f5a623", "#2f7dd1"}
PROP_IDS = {
    "laptop",
    "coffee",
    "docs",
    "calendar",
    "phone",
    "printer",
    "badge",
    "chair",
    "conveyor",
    "funnel",
    "scale",
    "gate",
    "blackbox",
    "ladder",
    "pipe",
    "mailbox",
    "idea",
    "question",
    "excl",
    "sweat",
    "anger",
    "zzz",
    "boom",
    "up",
    "arrow",
    "fork",
    "loop",
    "check",
    "cross",
    "balance",
    "gear",
    "network",
}


def _validate_silent_fields(value: Any, location: str) -> None:
    if isinstance(value, dict):
        for field, nested in value.items():
            field_location = f"{location}.{field}"
            if field in SILENT_FIELDS:
                raise ValueError(f"{field_location} 不允许；视频必须保持静音")
            _validate_silent_fields(nested, field_location)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_silent_fields(nested, f"{location}[{index}]")


def _validate_visual_numbers(item: dict[str, Any], location: str) -> None:
    for field in ("x", "y", "scale"):
        if field not in item:
            continue
        value = item[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{location}.{field} 必须是有限数")


def _validate_timing(item: dict[str, Any], location: str, shot_duration: float) -> None:
    if "at" not in item and "dur" not in item:
        return

    at = item.get("at", 0)
    if (
        isinstance(at, bool)
        or not isinstance(at, (int, float))
        or not math.isfinite(at)
        or at < 0
        or at > shot_duration
    ):
        raise ValueError(f"{location}.at 必须是镜头时长内的非负有限数")

    if "dur" not in item:
        return
    dur = item["dur"]
    if (
        isinstance(dur, bool)
        or not isinstance(dur, (int, float))
        or not math.isfinite(dur)
        or dur <= 0
        or at + dur > shot_duration
    ):
        raise ValueError(f"{location}.dur 必须是镜头剩余时长内的正有限数")


def _optional_objects(
    container: dict[str, Any], single: str, plural: str, location: str
) -> list[tuple[dict[str, Any], str]]:
    if single in container and plural in container:
        raise ValueError(f"{location}.{single} 与 {plural} 不能同时出现")

    if single in container:
        value = container[single]
        if not isinstance(value, dict):
            raise ValueError(f"{location}.{single} 必须是对象")
        return [(value, f"{location}.{single}")]

    if plural not in container:
        return []
    values = container[plural]
    if not isinstance(values, list):
        raise ValueError(f"{location}.{plural} 必须是数组")

    objects = []
    for index, value in enumerate(values):
        item_location = f"{location}.{plural}[{index}]"
        if not isinstance(value, dict):
            raise ValueError(f"{item_location} 必须是对象")
        objects.append((value, item_location))
    return objects


def _validate_character(
    character: dict[str, Any], location: str, shot_duration: float
) -> None:
    _validate_visual_numbers(character, location)
    _validate_timing(character, location, shot_duration)

    if "view" in character and character["view"] not in VIEWS:
        raise ValueError(f"{location}.view 仅支持 front 或 side")
    if "action" in character and character["action"] not in ACTIONS:
        raise ValueError(f"{location}.action 不受支持")


def validate_story(data: Any) -> None:
    """Raise ValueError when data violates the story-video contract."""
    if not isinstance(data, dict):
        raise ValueError("story 必须是 JSON 对象")

    _validate_silent_fields(data, "story")

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title 必须是非空字符串")
    if data.get("aspect") != "16:9":
        raise ValueError("aspect 必须是 16:9")

    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("shots 必须是非空数组")

    shot_ids: set[str] = set()
    for index, shot in enumerate(shots):
        location = f"shots[{index}]"
        if not isinstance(shot, dict):
            raise ValueError(f"{location} 必须是对象")

        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError(f"{location}.id 必须是非空字符串")
        if shot_id in shot_ids:
            raise ValueError(f"shot id 重复: {shot_id}")
        shot_ids.add(shot_id)

        duration = shot.get("duration")
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration <= 0
        ):
            raise ValueError(f"{location}.duration 必须是正数")

        if shot.get("pattern") not in PATTERNS:
            raise ValueError(f"{location}.pattern 不受支持")

        if "caption" in shot:
            caption = shot["caption"]
            if not isinstance(caption, str) or not caption.strip():
                raise ValueError(f"{location}.caption 必须是非空字符串")

        for character, character_location in _optional_objects(
            shot, "character", "characters", location
        ):
            _validate_character(character, character_location, duration)

        if "props" in shot:
            props = shot["props"]
            if not isinstance(props, list):
                raise ValueError(f"{location}.props 必须是数组")
            for prop_index, prop in enumerate(props):
                prop_location = f"{location}.props[{prop_index}]"
                if not isinstance(prop, dict):
                    raise ValueError(f"{prop_location} 必须是对象")
                if prop.get("id") not in PROP_IDS:
                    raise ValueError(f"{prop_location}.prop id 不受支持")
                _validate_visual_numbers(prop, prop_location)
                if "seed" in prop and not isinstance(prop["seed"], str):
                    raise ValueError(f"{prop_location}.seed 必须是字符串")
                _validate_timing(prop, prop_location, duration)

        for bubble, bubble_location in _optional_objects(
            shot, "bubble", "bubbles", location
        ):
            if "text" in bubble and (
                not isinstance(bubble["text"], str) or not bubble["text"].strip()
            ):
                raise ValueError(f"{bubble_location}.text 必须是非空字符串")
            _validate_timing(bubble, bubble_location, duration)

        for annotation, annotation_location in _optional_objects(
            shot, "annotation", "annotations", location
        ):
            if "text" in annotation and (
                not isinstance(annotation["text"], str)
                or not annotation["text"].strip()
            ):
                raise ValueError(f"{annotation_location}.text 必须是非空字符串")
            if (
                "color" in annotation
                and annotation["color"] not in ANNOTATION_COLORS
            ):
                raise ValueError(f"{annotation_location}.color 不受支持")
            _validate_timing(annotation, annotation_location, duration)

        if "camera" in shot:
            camera = shot["camera"]
            if not isinstance(camera, dict):
                raise ValueError(f"{location}.camera 必须是对象")
            camera_location = f"{location}.camera"
            _validate_visual_numbers(camera, camera_location)
            if "ease" in camera and not isinstance(camera["ease"], str):
                raise ValueError(f"{camera_location}.ease 必须是字符串")
            _validate_timing(camera, camera_location, duration)


def _load_story(story_path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"无效 JSON: {story_path}（不允许 {value}）")

    try:
        return json.loads(
            story_path.read_text(encoding="utf-8"), parse_constant=reject_constant
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"无效 JSON: {story_path}（第 {exc.lineno} 行，第 {exc.colno} 列）"
        ) from exc


def prepare_project(story_path: str | Path, project_dir: str | Path) -> None:
    """Validate a story and copy the required files into a project."""
    story_path = Path(story_path)
    project_dir = Path(project_dir)
    data = _load_story(story_path)
    validate_story(data)

    asset_sources = [SKILL_ROOT / "assets" / name for name in ASSET_NAMES]
    missing = [str(path) for path in asset_sources if not path.is_file()]
    index_path = project_dir / "index.html"
    template_path = SKILL_ROOT / "references" / "scene-composition.html"
    if not index_path.exists() and not template_path.is_file():
        missing.append(str(template_path))
    if missing:
        raise FileNotFoundError("缺少必需文件: " + ", ".join(missing))

    asset_dir = project_dir / "assets" / "story-video"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for source in asset_sources:
        shutil.copy2(source, asset_dir / source.name)
    story_destination = project_dir / "story.json"
    if not story_destination.exists() or not story_path.samefile(story_destination):
        shutil.copy2(story_path, story_destination)
    if not index_path.exists():
        shutil.copy2(template_path, index_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="校验 story.json")
    validate_parser.add_argument("story")

    prepare_parser = subparsers.add_parser("prepare", help="准备视频项目")
    prepare_parser.add_argument("story")
    prepare_parser.add_argument("project_dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate_story(_load_story(Path(args.story)))
        else:
            prepare_project(args.story, args.project_dir)
    except (OSError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
