import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = SKILL_ROOT / "scripts" / "story_video.py"


def load_story_video():
    spec = importlib.util.spec_from_file_location("story_video", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minimal_story():
    return {
        "title": "小黑的一天",
        "aspect": "16:9",
        "shots": [
            {
                "id": "shot-1",
                "duration": 2,
                "pattern": "character-state",
                "character": {"view": "front", "action": "idle"},
                "props": [{"id": "laptop"}],
            }
        ],
    }


class ScriptPresenceTests(unittest.TestCase):
    def test_story_video_script_exists(self):
        self.assertTrue(SCRIPT_PATH.is_file(), "scripts/story_video.py 尚未实现")


@unittest.skipUnless(SCRIPT_PATH.is_file(), "scripts/story_video.py 尚未实现")
class ValidateStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story_video = load_story_video()

    def test_accepts_minimal_story(self):
        self.story_video.validate_story(minimal_story())

    def test_rejects_empty_or_whitespace_title(self):
        for title in ("", "  \t"):
            with self.subTest(title=repr(title)):
                story = minimal_story()
                story["title"] = title

                with self.assertRaisesRegex(ValueError, "title"):
                    self.story_video.validate_story(story)

    def test_rejects_empty_shots(self):
        story = minimal_story()
        story["shots"] = []

        with self.assertRaisesRegex(ValueError, "shots"):
            self.story_video.validate_story(story)

    def test_rejects_empty_or_whitespace_shot_id(self):
        for shot_id in ("", "  \t"):
            with self.subTest(shot_id=repr(shot_id)):
                story = minimal_story()
                story["shots"][0]["id"] = shot_id

                with self.assertRaisesRegex(ValueError, "id"):
                    self.story_video.validate_story(story)

    def test_rejects_bool_duration(self):
        story = minimal_story()
        story["shots"][0]["duration"] = True

        with self.assertRaisesRegex(ValueError, "duration"):
            self.story_video.validate_story(story)

    def test_rejects_non_finite_duration(self):
        for duration in (float("nan"), float("inf")):
            with self.subTest(duration=duration):
                story = minimal_story()
                story["shots"][0]["duration"] = duration

                with self.assertRaisesRegex(ValueError, "duration"):
                    self.story_video.validate_story(story)

    def test_accepts_valid_character_array(self):
        story = minimal_story()
        del story["shots"][0]["character"]
        story["shots"][0]["characters"] = [
            {"view": "front", "action": "blink"},
            {"view": "side", "action": "walk"},
        ]

        self.story_video.validate_story(story)

    def test_rejects_invalid_single_character_view(self):
        story = minimal_story()
        story["shots"][0]["character"]["view"] = "back"

        with self.assertRaisesRegex(ValueError, "view"):
            self.story_video.validate_story(story)

    def test_rejects_invalid_character_array_action_and_view(self):
        for field, value in (("action", "dance"), ("view", "back")):
            with self.subTest(field=field):
                story = minimal_story()
                del story["shots"][0]["character"]
                story["shots"][0]["characters"] = [
                    {"view": "front", "action": "idle"}
                ]
                story["shots"][0]["characters"][0][field] = value

                with self.assertRaisesRegex(ValueError, field):
                    self.story_video.validate_story(story)

    def test_rejects_character_and_characters_together(self):
        story = minimal_story()
        story["shots"][0]["characters"] = [
            {"view": "side", "action": "walk"}
        ]

        with self.assertRaisesRegex(ValueError, "character.*characters"):
            self.story_video.validate_story(story)

    def test_rejects_invalid_optional_caption(self):
        for caption in ("", "  \t", 1):
            with self.subTest(caption=repr(caption)):
                story = minimal_story()
                story["shots"][0]["caption"] = caption

                with self.assertRaisesRegex(ValueError, "caption"):
                    self.story_video.validate_story(story)

    def test_accepts_nonempty_caption(self):
        story = minimal_story()
        story["shots"][0]["caption"] = "开始工作"

        self.story_video.validate_story(story)

    def test_rejects_non_object_camera(self):
        story = minimal_story()
        story["shots"][0]["camera"] = "close-up"

        with self.assertRaisesRegex(ValueError, "camera"):
            self.story_video.validate_story(story)

    def test_rejects_audio_fields_at_story_and_shot_levels(self):
        for field in ("audio", "bgm", "music", "voiceover", "narration", "sfx"):
            for level in ("story", "shot"):
                with self.subTest(field=field, level=level):
                    story = minimal_story()
                    target = story if level == "story" else story["shots"][0]
                    target[field] = "forbidden"

                    with self.assertRaisesRegex(ValueError, field):
                        self.story_video.validate_story(story)

    def test_rejects_audio_fields_nested_in_objects_and_arrays(self):
        cases = (
            ("audio", {"custom": {"audio": "forbidden"}}),
            ("voiceover", {"custom": [{"voiceover": "forbidden"}]}),
            ("narration", {"custom": {"items": [{"narration": "forbidden"}]}}),
            ("music", {"custom": [[{"music": "forbidden"}]]}),
            ("sfx", {"custom": {"items": [{"details": {"sfx": "forbidden"}}]}}),
            ("bgm", {"custom": [{"items": [{"bgm": "forbidden"}]}]}),
        )
        for field, nested in cases:
            with self.subTest(field=field):
                story = minimal_story()
                story.update(nested)

                with self.assertRaisesRegex(ValueError, field):
                    self.story_video.validate_story(story)

    def test_unknown_fields_remain_allowed(self):
        story = minimal_story()
        story["custom"] = {"enabled": True}
        story["shots"][0]["custom"] = "kept"

        self.story_video.validate_story(story)

    def test_rejects_single_and_plural_bubbles_or_annotations_together(self):
        for single, plural in (
            ("bubble", "bubbles"),
            ("annotation", "annotations"),
        ):
            with self.subTest(single=single):
                story = minimal_story()
                story["shots"][0][single] = {"text": "单个"}
                story["shots"][0][plural] = [{"text": "多个"}]

                with self.assertRaisesRegex(ValueError, f"{single}.*{plural}"):
                    self.story_video.validate_story(story)

    def test_rejects_non_object_bubble_or_annotation_items(self):
        for field, value in (
            ("bubble", "文本"),
            ("bubbles", ["文本"]),
            ("annotation", "标注"),
            ("annotations", ["标注"]),
        ):
            with self.subTest(field=field):
                story = minimal_story()
                story["shots"][0][field] = value

                with self.assertRaisesRegex(ValueError, field):
                    self.story_video.validate_story(story)

    def test_rejects_empty_bubble_or_annotation_text(self):
        for field in ("bubble", "bubbles", "annotation", "annotations"):
            with self.subTest(field=field):
                story = minimal_story()
                item = {"text": " "}
                story["shots"][0][field] = item if field in {
                    "bubble",
                    "annotation",
                } else [item]

                with self.assertRaisesRegex(ValueError, "text"):
                    self.story_video.validate_story(story)

    def test_rejects_unknown_annotation_color(self):
        for field in ("annotation", "annotations"):
            with self.subTest(field=field):
                story = minimal_story()
                item = {"text": "重点", "color": "#ffffff"}
                story["shots"][0][field] = item if field == "annotation" else [item]

                with self.assertRaisesRegex(ValueError, "color"):
                    self.story_video.validate_story(story)

    def test_accepts_plural_bubbles_and_annotations(self):
        story = minimal_story()
        story["shots"][0]["bubbles"] = [
            {"text": "你好", "at": 0.25, "dur": 0.5}
        ]
        story["shots"][0]["annotations"] = [
            {"text": "重点", "color": "#e2483d", "dur": 1}
        ]

        self.story_video.validate_story(story)

    def test_rejects_invalid_object_timing_numbers(self):
        cases = (
            ("character", {"view": "front", "at": True}),
            ("characters", [{"action": "idle", "dur": float("inf")}]),
            ("props", [{"id": "laptop", "at": float("nan")}]),
            ("bubble", {"text": "气泡", "dur": False}),
            ("bubbles", [{"text": "气泡", "at": "0"}]),
            ("annotation", {"text": "标注", "dur": float("nan")}),
            ("annotations", [{"text": "标注", "at": float("inf")}]),
            ("camera", {"dur": "1"}),
        )
        for field, value in cases:
            with self.subTest(field=field):
                story = minimal_story()
                if field in {"characters"}:
                    del story["shots"][0]["character"]
                story["shots"][0][field] = value

                with self.assertRaisesRegex(ValueError, "at|dur"):
                    self.story_video.validate_story(story)

    def test_rejects_object_timing_outside_shot(self):
        for timing in (
            {"at": -0.1},
            {"dur": 0},
            {"at": 2.1},
            {"dur": 2.1},
            {"at": 1.5, "dur": 0.6},
        ):
            with self.subTest(timing=timing):
                story = minimal_story()
                story["shots"][0]["camera"] = timing

                with self.assertRaisesRegex(ValueError, "at|dur"):
                    self.story_video.validate_story(story)

    def test_accepts_optional_object_timing_with_default_at(self):
        story = minimal_story()
        story["shots"][0]["camera"] = {"dur": 2}
        story["shots"][0]["props"][0].update({"at": 1.5, "dur": 0.5})

        self.story_video.validate_story(story)

    def test_rejects_invalid_visual_numbers(self):
        locations = ("character", "characters", "props", "camera")
        values = (True, "1", float("nan"), float("inf"))
        for location in locations:
            for field in ("x", "y", "scale"):
                for value in values:
                    with self.subTest(location=location, field=field, value=value):
                        story = minimal_story()
                        shot = story["shots"][0]
                        if location == "character":
                            target = shot["character"]
                        elif location == "characters":
                            del shot["character"]
                            shot["characters"] = [{"view": "front"}]
                            target = shot["characters"][0]
                        elif location == "props":
                            target = shot["props"][0]
                        else:
                            shot["camera"] = {}
                            target = shot["camera"]
                        target[field] = value

                        with self.assertRaisesRegex(ValueError, field):
                            self.story_video.validate_story(story)

    def test_rejects_non_string_prop_seed_and_camera_ease(self):
        for location, field in (("props", "seed"), ("camera", "ease")):
            for value in (True, 1, None, []):
                with self.subTest(location=location, field=field, value=value):
                    story = minimal_story()
                    shot = story["shots"][0]
                    if location == "props":
                        target = shot["props"][0]
                    else:
                        shot["camera"] = {}
                        target = shot["camera"]
                    target[field] = value

                    with self.assertRaisesRegex(ValueError, field):
                        self.story_video.validate_story(story)

    def test_accepts_declared_visual_fields(self):
        story = minimal_story()
        shot = story["shots"][0]
        shot["character"].update({"x": 100, "y": 200.5, "scale": 0.75})
        shot["props"][0].update(
            {"x": -10.5, "y": 0, "scale": 1.25, "seed": "laptop-1"}
        )
        shot["camera"] = {
            "x": 0,
            "y": -20,
            "scale": 1,
            "ease": "power2.inOut",
        }

        self.story_video.validate_story(story)

    def test_rejects_non_widescreen_aspect(self):
        story = minimal_story()
        story["aspect"] = "9:16"

        with self.assertRaisesRegex(ValueError, "aspect"):
            self.story_video.validate_story(story)

    def test_rejects_unknown_pattern(self):
        story = minimal_story()
        story["shots"][0]["pattern"] = "montage"

        with self.assertRaisesRegex(ValueError, "pattern"):
            self.story_video.validate_story(story)

    def test_rejects_unknown_character_action(self):
        story = minimal_story()
        story["shots"][0]["character"]["action"] = "dance"

        with self.assertRaisesRegex(ValueError, "action"):
            self.story_video.validate_story(story)

    def test_rejects_unknown_prop(self):
        story = minimal_story()
        story["shots"][0]["props"] = [{"id": "spaceship"}]

        with self.assertRaisesRegex(ValueError, "prop"):
            self.story_video.validate_story(story)

    def test_rejects_duplicate_shot_ids(self):
        story = minimal_story()
        story["shots"].append(dict(story["shots"][0]))

        with self.assertRaisesRegex(ValueError, "重复"):
            self.story_video.validate_story(story)

    def test_rejects_non_positive_duration(self):
        story = minimal_story()
        story["shots"][0]["duration"] = 0

        with self.assertRaisesRegex(ValueError, "duration"):
            self.story_video.validate_story(story)


@unittest.skipUnless(SCRIPT_PATH.is_file(), "scripts/story_video.py 尚未实现")
class PrepareProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story_video = load_story_video()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.fixture_root = self.root / "skill"
        asset_dir = self.fixture_root / "assets"
        asset_dir.mkdir(parents=True)
        for name in ("handdraw.js", "xiaohei.js", "microactions.js", "props.js"):
            (asset_dir / name).write_text(f"// {name}\n", encoding="utf-8")
        reference_dir = self.fixture_root / "references"
        reference_dir.mkdir(parents=True)
        (reference_dir / "scene-composition.html").write_text(
            "<!doctype html><title>scene</title>\n", encoding="utf-8"
        )
        self.story_path = self.root / "input-story.json"
        self.story_path.write_text(
            json.dumps(minimal_story(), ensure_ascii=False), encoding="utf-8"
        )
        self.story_video.SKILL_ROOT = self.fixture_root

    def test_prepare_copies_assets_story_and_template(self):
        project_dir = self.root / "project"

        self.story_video.prepare_project(self.story_path, project_dir)

        copied_assets = project_dir / "assets" / "story-video"
        for name in ("handdraw.js", "xiaohei.js", "microactions.js", "props.js"):
            self.assertEqual(
                (copied_assets / name).read_text(encoding="utf-8"), f"// {name}\n"
            )
        self.assertEqual(
            json.loads((project_dir / "story.json").read_text(encoding="utf-8")),
            minimal_story(),
        )
        self.assertEqual(
            (project_dir / "index.html").read_text(encoding="utf-8"),
            "<!doctype html><title>scene</title>\n",
        )

    def test_prepare_does_not_overwrite_existing_index(self):
        project_dir = self.root / "project"
        project_dir.mkdir()
        index_path = project_dir / "index.html"
        index_path.write_text("custom\n", encoding="utf-8")

        self.story_video.prepare_project(self.story_path, project_dir)

        self.assertEqual(index_path.read_text(encoding="utf-8"), "custom\n")

    def test_prepare_invalid_story_creates_no_project_artifacts(self):
        project_dir = self.root / "project"
        invalid_story_path = self.root / "invalid-story.json"
        story = minimal_story()
        story["title"] = " "
        invalid_story_path.write_text(
            json.dumps(story, ensure_ascii=False), encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "title"):
            self.story_video.prepare_project(invalid_story_path, project_dir)

        self.assertFalse(project_dir.exists())

    def test_prepare_skips_copy_when_story_is_already_at_destination(self):
        project_dir = self.root / "project"
        project_dir.mkdir()
        story_path = project_dir / "story.json"
        story_path.write_text(
            json.dumps(minimal_story(), ensure_ascii=False), encoding="utf-8"
        )

        self.story_video.prepare_project(story_path, project_dir)

        self.assertEqual(
            json.loads(story_path.read_text(encoding="utf-8")), minimal_story()
        )
        for name in ("handdraw.js", "xiaohei.js", "microactions.js", "props.js"):
            self.assertTrue((project_dir / "assets" / "story-video" / name).is_file())


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *map(str, args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )

    def write_story(self, story, name="story.json"):
        path = self.root / name
        path.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
        return path

    def test_validate_cli_succeeds_for_valid_story(self):
        result = self.run_cli("validate", self.write_story(minimal_story()))

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_validate_cli_reports_invalid_field(self):
        story = minimal_story()
        story["aspect"] = "9:16"

        result = self.run_cli("validate", self.write_story(story))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("aspect", result.stderr)

    def test_validate_cli_rejects_nonstandard_numeric_constants(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                story_path = self.root / f"story-{constant}.json"
                story_path.write_text(
                    json.dumps(minimal_story(), ensure_ascii=False).replace(
                        '"duration": 2', f'"duration": {constant}'
                    ),
                    encoding="utf-8",
                )

                result = self.run_cli("validate", story_path)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("无效 JSON", result.stderr)
                self.assertIn(constant, result.stderr)

    def test_prepare_cli_reports_invalid_story(self):
        story = minimal_story()
        story["title"] = " "

        result = self.run_cli(
            "prepare", self.write_story(story), self.root / "project"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("title", result.stderr)


if __name__ == "__main__":
    unittest.main()
