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


def test_hf_helpers_treat_none_as_an_empty_string():
    assert knowledge_video._hf_escape(None) == ""
    assert knowledge_video._hf_render_highlight(None) == ""
