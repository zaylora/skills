import json
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = SKILL_ROOT / "references"
EXAMPLE_ROOT = SKILL_ROOT / "examples"

PATTERNS = (
    "character-state",
    "dialogue",
    "journey",
    "process",
    "comparison",
    "cause-effect",
    "reveal",
    "summary",
)
VIEWS = ("front", "side")
ACTIONS = ("idle", "blink", "wave", "walk", "nod", "jump", "think", "surprise")
PROP_IDS = (
    "laptop", "coffee", "docs", "calendar", "phone", "printer", "badge", "chair",
    "conveyor", "funnel", "scale", "gate", "blackbox", "ladder", "pipe", "mailbox",
    "idea", "question", "excl", "sweat", "anger", "zzz", "boom", "up",
    "arrow", "fork", "loop", "check", "cross", "balance", "gear", "network",
)


class CompositionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.script_sources = []
        self.inline_scripts = []
        self.styles = []
        self._stack = []
        self._capture = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        ancestors = tuple(
            item["attrs"].get("id") for item in self._stack if item["attrs"].get("id")
        )
        record = {"tag": tag, "attrs": attributes, "ancestors": ancestors}
        self.elements.append(record)
        self._stack.append(record)
        if tag == "script":
            if attributes.get("src"):
                self.script_sources.append(attributes["src"])
            else:
                self._capture = "script"
                self._buffer = []
        elif tag == "style":
            self._capture = "style"
            self._buffer = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self._stack.pop()

    def handle_data(self, data):
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._capture == "script":
            self.inline_scripts.append("".join(self._buffer))
            self._capture = None
        elif tag == "style" and self._capture == "style":
            self.styles.append("".join(self._buffer))
            self._capture = None
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index]["tag"] == tag:
                del self._stack[index:]
                break


def parse_html(path):
    parser = CompositionParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def element_by_id(parser, element_id):
    matches = [item for item in parser.elements if item["attrs"].get("id") == element_id]
    if len(matches) != 1:
        raise AssertionError(f"期望唯一元素 #{element_id}，实际 {len(matches)} 个")
    return matches[0]


def nested_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_keys(child)


def css_declarations(style, selector):
    match = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", style, re.DOTALL)
    if not match:
        raise AssertionError(f"CSS 缺少规则 {selector}")
    return {
        key.strip(): value.strip()
        for key, value in re.findall(r"([\w-]+)\s*:\s*([^;]+);", match.group(1))
    }


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.agent_text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8", errors="replace"
        )

    def test_frontmatter_contains_only_name_and_description(self):
        match = re.match(r"\A---\s*\n(.*?)\n---", self.skill_text, re.DOTALL)
        self.assertIsNotNone(match, "SKILL.md 缺少 YAML frontmatter")
        keys = re.findall(r"^([a-zA-Z_][\w-]*):", match.group(1), re.MULTILINE)
        self.assertEqual(keys, ["name", "description"])

    def test_description_starts_with_use_when(self):
        match = re.search(r"^description:\s*(.+)$", self.skill_text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertTrue(match.group(1).strip('"\'').startswith("Use when"))

    def test_skill_has_no_forbidden_skill_or_absolute_repo_reference(self):
        self.assertNotIn("knowledge-video", self.skill_text)
        self.assertNotRegex(self.skill_text, r"(?i)[a-z]:[\\/]")
        self.assertNotRegex(self.skill_text, r"\.\.[\\/]")
        self.assertNotRegex(
            self.skill_text, r"(?i)(?:^|[\s`\"'=])skills[\\/]"
        )
        self.assertNotRegex(
            self.skill_text, r"(?m)(?:^|[\s`\"'=])/(?:[^/\s]+/)+"
        )

    def test_body_is_chinese_and_states_core_contract(self):
        body = self.skill_text.split("---", 2)[-1]
        self.assertRegex(body, r"[\u4e00-\u9fff]")
        for phrase in ("独立", "静音", "16:9", "Agent", "validate", "prepare"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_commands_use_resolved_skill_directory(self):
        self.assertIn("解析已安装技能的根目录", self.skill_text)
        self.assertIn(
            "python <skill-dir>/scripts/story_video.py validate", self.skill_text
        )
        self.assertIn(
            "python <skill-dir>/scripts/story_video.py prepare", self.skill_text
        )
        self.assertNotIn("python scripts/story_video.py", self.skill_text)

    def test_routes_all_required_references(self):
        for name in (
            "xiaohei-ip",
            "style-dna",
            "composition-patterns",
            "story-json-schema",
            "hyperframes-workflow",
            "scene-composition",
            "assets-preview",
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.skill_text)

    def test_requires_all_hyperframes_quality_gates(self):
        for command in (
            "npx hyperframes lint",
            "npx hyperframes check",
            "npx hyperframes preview",
            "npx hyperframes render",
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.skill_text)
        self.assertIn("preview 必须人工审阅", self.skill_text)
        self.assertRegex(
            self.skill_text, r"`?validate/inspect`? 仅用于旧版兼容"
        )
        self.assertIn("不作为主流程命令", self.skill_text)
        self.assertNotIn("npx hyperframes validate", self.skill_text)
        self.assertNotIn("npx hyperframes inspect", self.skill_text)

    def test_agent_interface_fields_match_contract(self):
        self.assertIn('display_name: "Story Video"', self.agent_text)
        self.assertIn(
            'short_description: "将故事主题制作成小黑手绘风格的静音 16:9 动画视频"',
            self.agent_text,
        )
        self.assertIn(
            'default_prompt: "使用 $story-video 把一个故事主题制作成小黑手绘风格的静音 16:9 动画视频。"',
            self.agent_text,
        )


class ReferenceContractTests(unittest.TestCase):
    REQUIRED_FILES = (
        REFERENCE_ROOT / "xiaohei-ip.md",
        REFERENCE_ROOT / "style-dna.md",
        REFERENCE_ROOT / "composition-patterns.md",
        REFERENCE_ROOT / "story-json-schema.md",
        REFERENCE_ROOT / "hyperframes-workflow.md",
        REFERENCE_ROOT / "scene-composition.html",
        REFERENCE_ROOT / "assets-preview.html",
        EXAMPLE_ROOT / "minimal-story.json",
    )

    def test_all_task3_files_exist(self):
        missing = [str(path.relative_to(SKILL_ROOT)) for path in self.REQUIRED_FILES if not path.is_file()]
        self.assertEqual(missing, [])

    def test_long_markdown_references_have_a_table_of_contents(self):
        for path in REFERENCE_ROOT.glob("*.md"):
            with self.subTest(path=path.name):
                lines = path.read_text(encoding="utf-8").splitlines()
                if len(lines) > 100:
                    self.assertIn("## 目录", lines[:30])

    def test_xiaohei_ip_defines_shape_persona_and_boundaries(self):
        text = (REFERENCE_ROOT / "xiaohei-ip.md").read_text(encoding="utf-8")
        for phrase in (
            "黑色实心蛋形身体", "白点眼", "细线四肢", "认真参与系统运转",
            "荒诞工作者", "正面", "侧面", "2-3", "卖萌五官", "复杂服饰", "真人化",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_style_dna_fixes_canvas_palette_type_and_prohibitions(self):
        text = (REFERENCE_ROOT / "style-dna.md").read_text(encoding="utf-8")
        for phrase in (
            "1920x1080", "#1a1a1a", "#e2483d", "#f5a623", "#2f7dd1", "2.2px",
            "圆端", "确定性抖动", "大量留白", "单镜单意", "中文系统字体",
            "20px", "60px", "letter-spacing: 0", "渐变", "阴影", "纸纹",
            "装饰卡片化", "网络图片",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_composition_patterns_define_exactly_the_validator_ids(self):
        text = (REFERENCE_ROOT / "composition-patterns.md").read_text(encoding="utf-8")
        ids = re.findall(r"^## Pattern: `([^`]+)`$", text, re.MULTILINE)
        self.assertEqual(tuple(ids), PATTERNS)
        for pattern in PATTERNS:
            section = re.search(
                rf"^## Pattern: `{re.escape(pattern)}`$(.*?)(?=^## Pattern:|\Z)",
                text,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(section)
            self.assertIn("适用场景", section.group(1))
            self.assertIn("核心布局", section.group(1))
            self.assertIn("优先资产", section.group(1))
        self.assertIn("不是额外框架", text)

    def test_story_schema_matches_validator_enums_and_timing_contract(self):
        text = (REFERENCE_ROOT / "story-json-schema.md").read_text(encoding="utf-8")
        for value in (*PATTERNS, *VIEWS, *ACTIONS, *PROP_IDS):
            with self.subTest(value=value):
                self.assertRegex(text, rf"(?<![\w-]){re.escape(value)}(?![\w-])")
        for phrase in (
            "duration", "at", "dur", "camera", "caption", "4-8", "2-shot", "纯静音",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_story_schema_matches_optional_and_mutually_exclusive_fields(self):
        text = (REFERENCE_ROOT / "story-json-schema.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"\| `caption` \| string \| 否 \|")
        self.assertRegex(text, r"\| `camera` \| object \| 否 \|")
        for phrase in (
            "character` 与 `characters` 不能同时出现",
            "bubble` 与 `bubbles` 不能同时出现",
            "annotation` 与 `annotations` 不能同时出现",
            "推荐使用复数数组",
            "audio`, `bgm`, `music`, `voiceover`, `narration",
            "at + dur",
            "元素中心点",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIsNotNone(re.search(r"annotation.*color.*可选", text, re.DOTALL))
        self.assertIn("若提供 `text`，必须是非空字符串", text)

    def test_workflow_is_standalone_and_covers_the_full_cli_sequence(self):
        text = (REFERENCE_ROOT / "hyperframes-workflow.md").read_text(encoding="utf-8")
        for phrase in (
            "Node.js >= 22", "FFmpeg", "npx hyperframes doctor", "npx hyperframes browser",
            "npx hyperframes init", "blank", "--non-interactive",
            "python <skill-dir>/scripts/story_video.py validate",
            "python <skill-dir>/scripts/story_video.py prepare", "Agent", "index.html",
            "npx hyperframes lint", "npx hyperframes check", "npx hyperframes preview",
            "npx hyperframes render", "http://localhost:<port>/#project/",
            "paused: true", "window.__timelines.main", "Math.random", "Date.now", "repeat: -1",
            "async", "setTimeout", "Promise",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("knowledge-video", text)
        self.assertNotRegex(text, r"(?i)(?:^|[\s`\"'(])[a-z]:[\\/]")
        self.assertNotRegex(text, r"\.\.[\\/]")

    def test_workflow_uses_current_hyperframes_quality_gate(self):
        text = (REFERENCE_ROOT / "hyperframes-workflow.md").read_text(encoding="utf-8")
        section = re.search(
            r"## HyperFrames 质量门(.*?)(?=^## )", text, re.MULTILINE | re.DOTALL
        )
        self.assertIsNotNone(section)
        commands = re.findall(r"^npx hyperframes (\w+)", section.group(1), re.MULTILINE)
        self.assertEqual(commands, ["lint", "check", "preview", "render"])
        self.assertIn("HyperFrames 0.7.60", text)
        self.assertIn("validate` 与 `inspect` 仅用于兼容旧版本", text)
        self.assertIn("不作为主流程", text)


class MinimalStoryFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = EXAMPLE_ROOT / "minimal-story.json"
        cls.data = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_fixture_is_exactly_two_shots_and_exercises_visual_fields(self):
        self.assertEqual(len(self.data["shots"]), 2)
        keys = set(nested_keys(self.data))
        for key in ("character", "props", "bubble", "annotation", "caption", "camera"):
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_fixture_is_valid_under_the_real_cli(self):
        result = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "story_video.py"), "validate", str(self.path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fixture_is_silent(self):
        forbidden = {"audio", "bgm", "music", "voice", "voiceover", "narration", "sound"}
        self.assertTrue(forbidden.isdisjoint(set(nested_keys(self.data))))


class SceneCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = REFERENCE_ROOT / "scene-composition.html"
        cls.text = cls.path.read_text(encoding="utf-8")
        cls.parser = parse_html(cls.path)
        cls.script = "\n".join(cls.parser.inline_scripts)
        cls.style = "\n".join(cls.parser.styles)
        cls.fixture = json.loads((EXAMPLE_ROOT / "minimal-story.json").read_text(encoding="utf-8"))

    def test_loads_gsap_3142_and_four_prepared_local_assets(self):
        expected = {
            "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js",
            "assets/story-video/handdraw.js", "assets/story-video/xiaohei.js",
            "assets/story-video/microactions.js", "assets/story-video/props.js",
        }
        self.assertTrue(expected.issubset(set(self.parser.script_sources)))

    def test_declares_local_font_face_and_uses_it_on_body(self):
        font_face = re.search(r"@font-face\s*\{([^}]+)\}", self.style, re.DOTALL)
        self.assertIsNotNone(font_face)
        self.assertRegex(font_face.group(1), r"font-family\s*:\s*[\"']StoryVideoSans[\"']")
        for family in ("Microsoft YaHei", "PingFang SC", "Hiragino Sans GB"):
            with self.subTest(family=family):
                self.assertIn(f'local("{family}")', font_face.group(1))
        body = css_declarations(self.style, "body")
        self.assertRegex(body["font-family"], r"^[\"']StoryVideoSans[\"']")

    def test_only_root_owns_composition_timing_attributes(self):
        timing = {"data-composition-id", "data-width", "data-height", "data-start", "data-duration"}
        owners = [item for item in self.parser.elements if timing.intersection(item["attrs"])]
        self.assertEqual(len(owners), 1)
        root = owners[0]["attrs"]
        self.assertEqual(root.get("id"), "root")
        self.assertEqual(root.get("data-composition-id"), "main")
        self.assertEqual((root.get("data-width"), root.get("data-height")), ("1920", "1080"))
        self.assertEqual(root.get("data-start"), "0")
        self.assertGreaterEqual(float(root["data-duration"]), 9)
        self.assertLessEqual(float(root["data-duration"]), 10)

    def test_scene_visibility_and_no_clip_class_follow_standalone_rules(self):
        scene1 = element_by_id(self.parser, "scene1")["attrs"]
        scene2 = element_by_id(self.parser, "scene2")["attrs"]
        self.assertNotIn("clip", scene1.get("class", "").split())
        self.assertNotIn("clip", scene2.get("class", "").split())
        self.assertNotRegex(scene1.get("style", ""), r"opacity\s*:\s*0")
        self.assertRegex(scene2.get("style", ""), r"opacity\s*:\s*0")

    def test_each_scene_has_camera_and_five_semantic_layers(self):
        for scene_id in ("scene1", "scene2"):
            descendants = [
                item for item in self.parser.elements if scene_id in item["ancestors"]
            ]
            classes = {
                name
                for item in descendants
                for name in item["attrs"].get("class", "").split()
            }
            with self.subTest(scene=scene_id):
                self.assertTrue(
                    {"camera", "character-layer", "props-layer", "bubble-layer", "annotation-layer", "caption-layer"}.issubset(classes)
                )

    def test_camera_layers_allow_expected_animation_overflow(self):
        for camera_id in ("s1-camera", "s2-camera"):
            with self.subTest(camera=camera_id):
                camera = element_by_id(self.parser, camera_id)["attrs"]
                self.assertIn("data-layout-allow-overflow", camera)

    def test_uses_real_asset_apis_and_multiple_microactions(self):
        for call in (
            "xiaohei.spawn(", "xiaohei.spawnSide(", "props.render(",
            "microactions.wave(", "microactions.walkCycle(",
        ):
            with self.subTest(call=call):
                self.assertIn(call, self.script)
        self.assertNotIn("microactions.nod(", self.script)
        self.assertNotIn("microactions.surprise(", self.script)

    def test_all_script_id_selectors_reference_real_dom_elements(self):
        dom_ids = {
            item["attrs"]["id"]
            for item in self.parser.elements
            if item["attrs"].get("id")
        }
        selector_ids = set(
            re.findall(r"[\"']#([A-Za-z_][\w-]*)(?:[\s.>+~:#\[\"'])", self.script)
        )
        self.assertEqual(sorted(selector_ids - dom_ids), [])

    def test_uses_paused_registered_timeline_and_from_entrances(self):
        self.assertRegex(self.script, r"gsap\.timeline\(\s*\{[^}]*paused\s*:\s*true")
        self.assertRegex(self.script, r"window\.__timelines\.main\s*=\s*tl")
        self.assertGreaterEqual(len(re.findall(r"\btl\.from\(", self.script)), 8)
        self.assertRegex(self.script, r"tl\.from\([^;]+,\s*0\.[123]\s*\)")

    def test_uses_css_push_as_the_only_scene1_exit(self):
        self.assertRegex(
            self.script,
            r"tl\.to\(\s*[\"']#scene1[\"']\s*,\s*\{[^}]*x\s*:\s*-1920",
        )
        self.assertRegex(
            self.script,
            r"tl\.fromTo\(\s*[\"']#scene2[\"']\s*,\s*\{[^}]*x\s*:\s*1920[^}]*opacity\s*:\s*1",
        )
        self.assertNotRegex(self.script, r"tl\.to\(\s*[\"']#scene1-[^\"']+")

    def test_template_timing_matches_fixture_absolute_at_values(self):
        starts = []
        elapsed = 0.0
        for shot in self.fixture["shots"]:
            starts.append(elapsed)
            elapsed += shot["duration"]

        root = element_by_id(self.parser, "root")["attrs"]
        self.assertEqual(float(root["data-duration"]), elapsed)
        transition_at = starts[1]
        for method in ("to", "fromTo"):
            self.assertRegex(
                self.script,
                rf"tl\.{method}\(\s*[\"']#scene[12][\"'].*?,\s*{transition_at:g}\s*\);",
            )

        for index, shot in enumerate(self.fixture["shots"], start=1):
            start = starts[index - 1]
            camera_at = start + shot["camera"]["at"]
            self._assert_from_at(f"#s{index}-camera", camera_at, shot["camera"]["dur"])

            for prop in shot["props"]:
                prop_at = start + prop["at"]
                self._assert_from_at(
                    f"#s{index}-{prop['id']}", prop_at, prop["dur"]
                )

            self._assert_from_at(
                f"#s{index}-annotation", start + shot["annotation"]["at"]
            )
            self._assert_from_at(
                f"#s{index}-bubble", start + shot["bubble"]["at"]
            )

        self.assertNotIn(".props-layer .prop", self.script)
        self.assertRegex(
            self.script,
            r"microactions\.wave\(tl, frontActor, \{ at: 0\.8, duration: 1\.1",
        )
        self.assertRegex(
            self.script,
            r"microactions\.walkCycle\(tl, sideActor, \{ at: 5\.3, duration: 1\.6",
        )

    def test_template_css_placement_matches_fixture_center_coordinates(self):
        for index, shot in enumerate(self.fixture["shots"], start=1):
            camera = css_declarations(self.style, f"#s{index}-camera")
            self.assertEqual(camera["--fixture-x"], f"{shot['camera']['x']:g}px")
            self.assertEqual(camera["--fixture-y"], f"{shot['camera']['y']:g}px")
            self.assertEqual(camera["--fixture-scale"], f"{shot['camera']['scale']:g}")

            items = [(f"#s{index}-character", shot["character"])]
            items.extend(
                (f"#s{index}-{prop['id']}", prop) for prop in shot["props"]
            )
            for selector, item in items:
                with self.subTest(selector=selector):
                    declarations = css_declarations(self.style, selector)
                    self.assertEqual(declarations["left"], f"{item['x']:g}px")
                    self.assertEqual(declarations["top"], f"{item['y']:g}px")
                    self.assertEqual(
                        declarations["--fixture-scale"], f"{item['scale']:g}"
                    )

    def _assert_from_at(self, selector, at, duration=None):
        match = re.search(
            rf"tl\.from\(\s*[\"']{re.escape(selector)}[\"']\s*,\s*\{{([^}}]+)\}}\s*,\s*{at:g}\s*\);",
            self.script,
        )
        self.assertIsNotNone(match, f"{selector} 缺少绝对入口时间 {at:g}")
        if duration is not None:
            self.assertRegex(match.group(1), rf"duration\s*:\s*{duration:g}(?:\D|$)")

    def test_contains_fixture_text_instead_of_placeholder_copy(self):
        expected = {self.fixture["title"]}
        for shot in self.fixture["shots"]:
            expected.add(shot["caption"])
            expected.add(shot["bubble"]["text"])
            expected.add(shot["annotation"]["text"])
        for value in expected:
            with self.subTest(value=value):
                self.assertIn(value, self.text)
        self.assertNotRegex(self.text, r"\{\{[^}]+\}\}|TODO|PLACEHOLDER")

    def test_template_has_no_audio_gradients_or_nondeterministic_async_code(self):
        self.assertNotRegex(self.text.lower(), r"<\s*(audio|video)\b|gradient\s*\(")
        for token in ("Math.random", "Date.now", "repeat: -1", "async ", "setTimeout", "Promise", "<br"):
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)


class AssetsPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = REFERENCE_ROOT / "assets-preview.html"
        cls.text = cls.path.read_text(encoding="utf-8")
        cls.parser = parse_html(cls.path)
        cls.script = "\n".join(cls.parser.inline_scripts)

    def test_preview_uses_reference_relative_assets_and_both_views(self):
        expected = {
            "../assets/handdraw.js", "../assets/xiaohei.js",
            "../assets/microactions.js", "../assets/props.js",
        }
        self.assertTrue(expected.issubset(set(self.parser.script_sources)))
        self.assertIn("xiaohei.spawn(", self.script)
        self.assertIn("xiaohei.spawnSide(", self.script)

    def test_preview_names_all_actions_and_builds_finite_demos(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                self.assertRegex(self.script, rf"[\"']{re.escape(action)}[\"']")
        self.assertIn("microactions.dispatch(", self.script)
        self.assertNotIn("repeat: -1", self.text)

    def test_preview_renders_the_real_complete_prop_catalog(self):
        self.assertRegex(self.script, r"props\.list\(\)\.forEach\(")
        self.assertIn("props.render(", self.script)
        self.assertEqual(len(PROP_IDS), 32)

    def test_preview_is_not_a_hyperframes_composition(self):
        self.assertNotIn("data-composition-id", self.text)
        self.assertNotIn("window.__timelines", self.text)


if __name__ == "__main__":
    unittest.main()
