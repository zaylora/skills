import importlib.util
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
