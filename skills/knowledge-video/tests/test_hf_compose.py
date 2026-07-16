import argparse
import importlib.util
import json
from types import SimpleNamespace
from pathlib import Path


_SCRIPT = Path(__file__).parents[1] / "scripts" / "knowledge_video.py"
_SPEC = importlib.util.spec_from_file_location("knowledge_video", _SCRIPT)
knowledge_video = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(knowledge_video)


def test_hf_escape_escapes_html_characters_in_order():
    assert knowledge_video._hf_escape('<b>&"') == "&lt;b&gt;&amp;&quot;"


def test_hf_render_highlight_wraps_escaped_highlight_content():
    assert knowledge_video._hf_render_highlight("看 ==重点== 词") == (
        '看 <span class="amber">重点</span> 词'
    )


def test_hf_render_highlight_escapes_plain_and_highlight_content():
    assert knowledge_video._hf_render_highlight("a<b ==c==") == (
        'a&lt;b <span class="amber">c</span>'
    )


def test_hf_render_highlight_wraps_each_highlight_marker_separately():
    assert knowledge_video._hf_render_highlight("==a== ... ==b==") == (
        '<span class="amber">a</span> ... <span class="amber">b</span>'
    )


def test_hf_render_highlight_escapes_html_characters_inside_a_highlight():
    assert knowledge_video._hf_render_highlight('==& <>"==') == (
        '<span class="amber">&amp; &lt;&gt;&quot;</span>'
    )


def test_hf_render_highlight_leaves_empty_markers_unhighlighted():
    assert knowledge_video._hf_render_highlight("====") == "===="
    assert knowledge_video._hf_render_highlight("==text==") == (
        '<span class="amber">text</span>'
    )


def test_hf_helpers_treat_none_as_an_empty_string():
    assert knowledge_video._hf_escape(None) == ""
    assert knowledge_video._hf_render_highlight(None) == ""


def test_hf_scene_title_renders_icon_title_subtitle_and_highlighted_text():
    scene = knowledge_video._hf_scene_title({
        "icon": "<星>",
        "slide_title": "==知识== <开场>",
        "subtitle": "副标题 ==重点==",
        "narration": "旁白 <内容>",
    }, {"main": "#38bdf8"})

    assert '<div class="kicker">&lt;星&gt;</div>' in scene
    assert '<div class="hero-title"><span class="amber">知识</span> &lt;开场&gt;</div>' in scene
    assert '<div class="hero-sub">副标题 <span class="amber">重点</span></div>' in scene
    assert '<div class="sub-desc">旁白 &lt;内容&gt;</div>' in scene


def test_hf_scene_content_renders_text_layout_without_image():
    scene = knowledge_video._hf_scene_content({
        "index": 0,
        "slide_title": "章节 ==标题==",
        "text": "要点 <一>",
        "narration": "说明 ==重点==",
    }, {"main": "#38bdf8"})

    assert '<div class="kicker">章节 <span class="amber">标题</span></div>' in scene
    assert '<div class="scene-number">01</div>' in scene
    assert '<div class="lead">要点 &lt;一&gt;</div>' in scene
    assert '<div class="sub-desc">说明 <span class="amber">重点</span></div>' in scene
    assert "<img" not in scene


def test_hf_scene_content_renders_split_layout_with_image():
    scene = knowledge_video._hf_scene_content({
        "index": 9,
        "slide_title": "章节",
        "text": "要点",
        "narration": "说明",
        "image": 'assets/<image>.png',
    }, {"main": "#38bdf8"})

    assert 'class="scene-content split-layout"' in scene
    assert '<div class="scene-number">10</div>' in scene
    assert '<img src="assets/&lt;image&gt;.png" alt="">' in scene


def test_hf_scene_summary_renders_each_point_with_a_check_mark_and_image():
    scene = knowledge_video._hf_scene_summary({
        "slide_title": "==总结==",
        "points": ["第一 <点>", "第二 ==重点=="],
        "narration": "收束旁白",
        "image": "assets/summary.png",
    }, {"main": "#38bdf8"})

    assert 'class="scene-summary split-layout"' in scene
    assert '<div class="hero-title"><span class="amber">总结</span></div>' in scene
    assert scene.count('class="check-mark"') == 2
    assert '<span class="check-mark">&#10003;</span>' in scene
    assert '<span>第一 &lt;点&gt;</span>' in scene
    assert '<span>第二 <span class="amber">重点</span></span>' in scene
    assert '<div class="sub-desc">收束旁白</div>' in scene
    assert '<img src="assets/summary.png" alt="">' in scene


def test_collect_hf_segments_enumerates_title_content_and_summary(tmp_path):
    slides = [
        knowledge_video.SlideData(
            type="title", title="开场", subtitle="副标题", narration="标题旁白", icon="星"
        ),
        knowledge_video.SlideData(
            type="content", title="内容", icon="书", key_points=[
                knowledge_video.KeyPoint(text="第一点", narration="第一点旁白"),
                knowledge_video.KeyPoint(text="第二点", narration="第二点旁白"),
            ]
        ),
        knowledge_video.SlideData(
            type="summary", title="总结", narration="总结旁白", icon="勾",
            key_points=[knowledge_video.KeyPoint(text="要点")],
        ),
    ]

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, tmp_path / "hf")

    assert [(segment["index"], segment["type"], segment["slide_title"])
            for segment in segments] == [
        (0, "title", "开场"),
        (1, "content", "内容"),
        (2, "content", "内容"),
        (3, "summary", "总结"),
    ]
    assert segments[0]["subtitle"] == "副标题"
    assert segments[1]["text"] == "第一点"
    assert segments[1]["narration"] == "第一点旁白"
    assert segments[3]["points"] == ["要点"]
    assert all(segment["start"] == 0.0 and segment["duration"] == 0.0
               and segment["audio"] == "" for segment in segments)


def test_collect_hf_segments_copies_content_key_point_image(tmp_path):
    image = tmp_path / "source.png"
    image.write_bytes(b"image")
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="要点", image="source.png", narration="旁白"),
        ]
    )]
    hf_dir = tmp_path / "hf"

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, hf_dir)

    assert segments[0]["image"] == "assets/images/source.png"
    assert (hf_dir / "assets" / "images" / "source.png").read_bytes() == b"image"


def test_collect_hf_segments_title_ignores_slide_image(tmp_path):
    image = tmp_path / "title.png"
    image.write_bytes(b"image")
    slides = [knowledge_video.SlideData(
        type="title", title="开场", image="title.png", narration="标题旁白"
    )]

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, tmp_path / "hf")

    assert "image" not in segments[0]


def test_collect_hf_segments_adds_summary_points_and_image(tmp_path):
    image = tmp_path / "summary.png"
    image.write_bytes(b"image")
    slides = [knowledge_video.SlideData(
        type="summary", title="总结", image="summary.png", narration="总结旁白",
        key_points=[
            knowledge_video.KeyPoint(text="要点一"),
            knowledge_video.KeyPoint(text="要点二"),
        ],
    )]
    hf_dir = tmp_path / "hf"

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, hf_dir)

    assert segments[0]["points"] == ["要点一", "要点二"]
    assert segments[0]["image"] == "assets/images/summary.png"
    assert (hf_dir / "assets" / "images" / "summary.png").exists()


def test_collect_hf_segments_skips_missing_images(tmp_path, capsys):
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="要点", image="missing.png", narration="旁白"),
        ]
    )]

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, tmp_path / "hf")

    assert "image" not in segments[0]
    assert "[warn]" in capsys.readouterr().out


def test_collect_hf_segments_rejects_parent_directory_images(tmp_path, capsys):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (tmp_path / "outside.png").write_bytes(b"outside")
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="要点", image="../outside.png"),
        ]
    )]

    segments = knowledge_video.collect_hf_segments(slides, work_dir, tmp_path / "hf")

    assert "image" not in segments[0]
    assert "[warn]" in capsys.readouterr().out


def test_collect_hf_segments_rejects_absolute_images(tmp_path, capsys):
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="要点", image=str(outside)),
        ]
    )]

    segments = knowledge_video.collect_hf_segments(slides, tmp_path / "work", tmp_path / "hf")

    assert "image" not in segments[0]
    assert "[warn]" in capsys.readouterr().out


def test_collect_hf_segments_disambiguates_same_basename_sources(tmp_path):
    (tmp_path / "first").mkdir()
    (tmp_path / "second").mkdir()
    (tmp_path / "first" / "photo.png").write_bytes(b"first")
    (tmp_path / "second" / "photo.png").write_bytes(b"second")
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="第一张", image="first/photo.png"),
            knowledge_video.KeyPoint(text="第二张", image="second/photo.png"),
        ]
    )]
    hf_dir = tmp_path / "hf"

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, hf_dir)

    assert segments[0]["image"] == "assets/images/photo.png"
    assert segments[1]["image"] != segments[0]["image"]
    assert (hf_dir / segments[0]["image"]).read_bytes() == b"first"
    assert (hf_dir / segments[1]["image"]).read_bytes() == b"second"


def test_collect_hf_segments_preserves_conflicting_existing_output(tmp_path):
    (tmp_path / "photo.png").write_bytes(b"source")
    hf_dir = tmp_path / "hf"
    existing = hf_dir / "assets" / "images" / "photo.png"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing")
    slides = [knowledge_video.SlideData(
        type="content", title="内容", key_points=[
            knowledge_video.KeyPoint(text="要点", image="photo.png"),
        ]
    )]

    segments = knowledge_video.collect_hf_segments(slides, tmp_path, hf_dir)

    assert segments[0]["image"] != "assets/images/photo.png"
    assert existing.read_bytes() == b"existing"
    assert (hf_dir / segments[0]["image"]).read_bytes() == b"source"


def test_hf_prepare_uses_eligible_audio_segments_with_content_image(tmp_path, monkeypatch):
    work_dir = tmp_path / "work"
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True)
    (work_dir / "content.png").write_bytes(b"content image")
    (audio_dir / "slide-01.mp3").write_bytes(b"title audio")
    (audio_dir / "slide-02b.mp3").write_bytes(b"content audio")
    slides_path = work_dir / "slides.json"
    slides_path.write_text(json.dumps({
        "title": "视频标题",
        "slides": [
            {
                "type": "title",
                "title": "开场",
                "subtitle": "副标题",
                "narration": "标题旁白",
            },
            {
                "type": "content",
                "title": "内容",
                "key_points": [
                    {"text": "没有旁白的要点"},
                    {
                        "text": "带图片的要点",
                        "narration": "内容旁白",
                        "image": "content.png",
                    },
                ],
            },
        ],
    }, ensure_ascii=False), encoding="utf-8")
    durations = {"slide-01.mp3": 1.25, "slide-02b.mp3": 2.5}
    monkeypatch.setattr(
        knowledge_video, "_ffprobe_duration", lambda path: durations[path.name]
    )

    def fake_run(command, **_kwargs):
        Path(command[-1]).write_bytes(b"concatenated narration")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(knowledge_video.subprocess, "run", fake_run)
    hf_dir = tmp_path / "hf"

    knowledge_video.cmd_hf_prepare(argparse.Namespace(
        json=str(slides_path), work_dir=str(work_dir), hf_dir=str(hf_dir),
    ))

    timeline = json.loads((hf_dir / "timeline.json").read_text(encoding="utf-8"))
    assert timeline["title"] == "视频标题"
    assert timeline["total_duration"] == 3.75
    assert [(segment["audio"], segment["start"], segment["duration"])
            for segment in timeline["segments"]] == [
        ("slide-01.mp3", 0.0, 1.25),
        ("slide-02b.mp3", 1.25, 2.5),
    ]
    assert timeline["segments"][0]["subtitle"] == "副标题"
    assert timeline["segments"][1]["text"] == "带图片的要点"
    assert timeline["segments"][1]["image"] == "assets/images/content.png"
    assert (hf_dir / "assets" / "images" / "content.png").read_bytes() == b"content image"
    assert (hf_dir / "assets" / "narration.mp3").read_bytes() == b"concatenated narration"


def test_compose_hf_html_builds_deterministic_timed_scenes_with_audio_and_image():
    timeline = {
        "total_duration": 8.5,
        "segments": [
            {
                "index": 0,
                "type": "title",
                "start": 0.0,
                "duration": 3.0,
                "slide_title": "开场",
                "subtitle": "副标题",
                "narration": "标题旁白",
            },
            {
                "index": 1,
                "type": "content",
                "start": 3.0,
                "duration": 5.5,
                "slide_title": "内容",
                "text": "要点",
                "narration": "内容旁白",
                "image": "assets/images/content.png",
            },
        ],
    }

    document = knowledge_video.compose_hf_html(timeline)

    assert document == knowledge_video.compose_hf_html(timeline)
    assert 'https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js' in document
    assert '<main class="bg" data-duration="8.5">' in document
    assert '<audio id="narration" src="assets/narration.mp3"></audio>' in document
    assert document.count('<section class="clip scene scene-') == 2
    assert 'data-start="0.0" data-duration="3.0"' in document
    assert 'data-start="3.0" data-duration="5.5"' in document
    assert '<img src="assets/images/content.png" alt="">' in document
    assert '@font-face' in document and 'src:local(' in document
    assert '1920px' in document and '1080px' in document
    assert '.bg' in document and '.scene' in document and '.amber' in document
    assert '.split' in document and '.center-col' in document and '.checks' in document
    assert '.progress' in document
    assert 'window.__timelines = ' in document
    assert 'gsap.timeline({ paused: true })' in document
    assert 'autoAlpha' in document and 'stagger: 0.4' in document
    assert 'window.__timelines["main"] = tl;' in document
    assert 'Date.now' not in document
    assert 'Math.random' not in document
    assert 'fetch(' not in document
