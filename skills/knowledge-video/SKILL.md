---
name: knowledge-video
description: 面向科普/讲解的自动视频流水线：调研→撰稿→PPT截图→TTS→逐段合成→整片输出。用户给主题/要求/关键词即可生成 1080p 知识讲解视频。
---

# 知识讲解视频生成器

生成 1080p（1920×1080）知识讲解/科普视频的 **Agent 引导流程**。

你（Agent）是导演，负责调研、撰稿、审查；Python 脚本是工具人，负责截图、配音、剪辑。

---

## 触发条件

用户要求生成：科普视频、知识讲解视频、解说视频、教程视频，或提到 knowledge-video。

## 前置依赖（首次使用前确认）

**Python 侧（调研/撰稿/TTS + hf-prepare 辅助脚本，必需）：**

```bash
pip install -r skills/knowledge-video/requirements.txt
```

还需要 `ffmpeg`（`brew install ffmpeg` / `choco install ffmpeg`）。

`hf-prepare` 和 `hf-compose` 是独立的 Python 命令：生成 `timeline.json` 与 `index.html` 时不需要安装 Node.js 或 HyperFrames。只有选择路径 A 渲染、检查或出片时，才需要通过 `npx hyperframes` 调用 HyperFrames。

**渲染引擎（二选一）：**
- **路径 A（推荐）hyperframes**：需 **Node.js 22+**，用 `npx hyperframes` 免安装调用，首次 `npx hyperframes browser ensure` 备好渲染 Chrome
- **路径 B（fallback）Playwright**：`playwright install chromium`（无 Node 环境时用）

---

## 流程：7 个步骤，逐步执行

### Step 1 — 明确需求

从用户消息中提取以下信息。缺失的主动询问：

| 信息 | 默认值 |
|------|--------|
| 主题 | （必须有） |
| 受众 | 普通人 / 小白 |
| 时长 | 2-3 分钟 |
| 风格 | 轻松科普 |
| 语音偏好 | 男声 / 女声（默认使用 xskill 海螺语音，效果更自然） |

确定工作目录名：`out/<主题简称>-video/`

### Step 2 — 调研素材

使用 **WebSearch** 搜索主题，收集 3-5 条有实质内容的资料。

搜索策略：
- 第一轮：`<主题> 是什么 最新进展`
- 第二轮：`<主题> 普通人 机会`（或针对受众的角度）
- 如果是技术主题，加一轮英文搜索

提取并整理：
- 核心定义 / 关键数据 / 时间节点
- 最新进展（谁在做、做到什么程度）
- 与受众的关系（能干嘛、怎么参与）

> 如果用户已提供完整文案或详细素材，可跳过此步。

### Step 3 — 撰写结构化脚本

根据调研结果，撰写完整视频脚本。输出 JSON 并保存。

**创建工作目录并写入 slides.json：**

```python
import json
from pathlib import Path

work_dir = Path("out/<项目名>-video")
work_dir.mkdir(parents=True, exist_ok=True)

slides_data = {
    "title": "视频总标题",
    "slides": [
        # ... 见下方格式 ...
    ]
}

(work_dir / "slides.json").write_text(
    json.dumps(slides_data, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

#### JSON 格式

每个 content slide 的 `key_points` 使用对象数组，每个 key_point 有独立的 `text`、`image`、`narration`，渲染时每个 key_point 生成一页子幻灯片（左文右图 + 描述文字），音频与画面一一对齐。

```json
{
  "title": "视频总标题",
  "slides": [
    {
      "type": "title",
      "title": "抓人眼球的开场标题",
      "subtitle": "一句话点明价值",
      "icon": "🤖",
      "key_points": [],
      "narration": "开场口播 30-50 字（短而有力，避免标题页长时间停留）"
    },
    {
      "type": "content",
      "title": "小标题",
      "icon": "💡",
      "key_points": [
        {
          "text": "要点标题（15-30字，完整表达核心信息）",
          "image": "images/xxx.png",
          "narration": "本要点口播 40-80 字"
        },
        {
          "text": "要点标题 2",
          "image": "images/yyy.png",
          "narration": "本要点口播 40-80 字"
        }
      ],
      "narration": ""
    },
    {
      "type": "summary",
      "title": "总结 & 行动",
      "icon": "🎯",
      "key_points": ["核心收获1", "核心收获2", "今天就能做的事"],
      "narration": "总结口播 60-100 字"
    }
  ]
}
```

**字段说明：**
| 字段 | 用途 |
|------|------|
| `type` | `title` 居中大标题页 / `content` 编号要点页 / `summary` 打勾总结页 |
| `title` | 幻灯片上的标题 |
| `key_points` | content 类型用对象数组 `{text, image, narration}`；summary 类型用字符串数组 |
| `key_points[].text` | 显示在幻灯片上的要点标题，15-30 字，完整表达核心信息（不是缩写短语） |
| `key_points[].image` | 配图路径（相对工作目录），每个要点一张图 |
| `key_points[].narration` | 该要点的独立口播文案，40-80 字 |
| `narration` | TTS 朗读文案。title/summary 页填写；content 页留空（由各 key_point.narration 替代） |
| `icon` | 可选 emoji，显示在标题旁 |
| `subtitle` | 仅 title 类型使用，支持 `==文字==` 语法将文字高亮为强调色 |
| `image` | title/summary 页可选配图路径 |

**布局说明：** narration 文本会同时显示在画面上作为描述文字（标题页/总结页底部、内容页要点下方），确保画面内容饱满。

**页数建议：** 1-2 分钟 → 4-5 页 ｜ 2-3 分钟 → 5-7 页 ｜ 3-5 分钟 → 7-10 页

#### 口播文案写作规范（严格遵守）

**风格：**
- 口语化，像跟朋友面对面聊天
- 长短句交替，有节奏感，适合朗读
- 用"你"称呼观众

**开场（title 页）：**
- 用让人意外的事实、数据或反直觉问题开头
- 口播控制在 30-50 字（标题页内容少，音频不宜过长）
- ❌ "大家好，今天聊聊 XXX"
- ✅ "两天，十万颗星标——GitHub 最快纪录。打破它的不是科技巨头，而是一个程序员周末的开源项目。"

**主体（content 页）：**
- 每个 key_point 聚焦一个要点，narration 40-80 字
- 必须包含至少一个具体数据、案例或类比
- 段间自然过渡
- ❌ "接下来看看趋势"
- ✅ "光有技术还不够，关键是谁在真金白银地砸钱？"

**总结（summary 页）：**
- 提炼"一句话记住"的核心，不要复述
- 结尾给一个**今天就能做**的具体行动
- ❌ "以上就是今天的内容"
- ✅ "今晚花十分钟，去 GitHub 把 README 读完——这是你进入这个领域成本最低的方式。"

**禁止清单：**
- ❌ "让我们来看看..." / "关于 XXX..."
- ❌ 同一个主题名出现超过 2 次
- ❌ "首先...其次...最后..."
- ❌ 自我指令出现在文案中（"用一句话说清"、"给建议"）

**幻灯片 key_points 规范：**
- text 字段 15-30 字，完整表达核心信息（会显示为大标题）
- narration 字段是该要点的口播文案，40-80 字（会同时显示在画面上作为描述）
- text 不是缩写短语，要让观众一眼看懂要点
- 示例：口播 "硬件成本从百万降到两万" → text "硬件成本从百万级降到两万，门槛大幅降低"

#### 检查点

将脚本展示给用户，简要说明结构（几页、每页主题）。用户确认后继续。

### Step 4 — 语音合成（TTS 在渲染之前）

**重要：** 视频模式下，TTS 必须先于渲染执行——render 需要音频时长来控制录制时长。

#### 4a — 选择配音角色

优先使用 **xskill 海螺语音**（Minimax TTS），效果更自然真实。先查看可用音色：

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py xskill-voices --tag 男
python3 skills/knowledge-video/scripts/knowledge_video.py xskill-voices --tag 女
```

根据视频风格选择音色：

| 场景 | 推荐音色 ID | 名称 |
|------|------------|------|
| 科普解说（男声） | `male-qn-qingse` | 青涩青年 |
| 专业权威（男声） | `male-qn-jingying` | 精英青年 |
| 知性讲解（女声） | `female-chengshu` | 成熟女性 |
| 活泼风格（女声） | `female-shaonv` | 少女 |
| 甜美旁白（女声） | `female-tianmei` | 甜美女性 |
| 御姐解说（女声） | `female-yujie` | 御姐 |

#### 4b — 执行语音合成

**方式一：xskill 海螺语音（推荐，效果更好）**

需要 `XSKILL_API_KEY` 环境变量（获取方式见 xskill-api skill）。

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py tts \
  --json <work-dir>/slides.json \
  --work-dir <work-dir> \
  --engine xskill \
  --voice-id male-qn-qingse
```

可选参数：
- `--tts-model speech-2.8-hd` — 模型版本（默认，效果最好）
- `--tts-model speech-2.8-turbo` — 速度更快，略降质量

脚本会批量提交所有语音任务并行合成，自动轮询下载。

**方式二：Edge TTS（免费备选，无需 API Key）**

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py tts \
  --json <work-dir>/slides.json \
  --work-dir <work-dir> \
  --engine edge \
  --voice zh-CN-YunxiNeural
```

Edge TTS 可用语音：`zh-CN-YunxiNeural`（男）、`zh-CN-XiaoxiaoNeural`（女）、`zh-CN-YunjianNeural`（沉稳男）、`zh-CN-XiaoyiNeural`（活泼女）。完整列表：`python3 skills/knowledge-video/scripts/knowledge_video.py list-voices`

**输出：** `<work-dir>/audio/slide-01.mp3`、`slide-02a.mp3`、`slide-02b.mp3` ...

每个 key_point 有独立 narration 时，生成带后缀的音频（`a`/`b`/`c`）。

### Step 5 — 渲染视频（两种引擎，任选其一）

> **推荐 hyperframes（路径 A）**：确定性逐帧渲染 + GSAP 精细动画，一步出片（render 即含音频合成）。
> **无 Node 环境时用 Playwright（路径 B）**：原有录屏方式，作为 fallback。

#### 路径 A（推荐）— hyperframes

前置：Node.js 22+ 与 `ffmpeg`。首次使用先备好渲染浏览器：

```bash
npx hyperframes doctor          # 检查环境
npx hyperframes browser ensure  # 下载/定位渲染用 Chrome
```

**A-1 初始化 hyperframes 项目**（在工作目录外新建，例如 `out/<主题>-hf`）：

```bash
HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init <hf-dir> --example blank --non-interactive
```

**A-2 生成旁白轨 + 场景时间轴**（拼接音频、按音频时长算好每段 start/duration）：

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py hf-prepare \
  --json <work-dir>/slides.json \
  --work-dir <work-dir> \
  --hf-dir <hf-dir>
```

产出 `<hf-dir>/assets/narration.mp3` + `<hf-dir>/timeline.json`（每段含 index/audio/start/duration + type/title/text/narration 等文案元信息）。

**A-3 自动生成 composition**：

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py hf-compose --hf-dir <hf-dir>
```

自动从 `timeline.json` 生成 `<hf-dir>/index.html`，其中包含场景、GSAP 动画、配图和进度条，无需手写。后续 `npm run check` 与 `npm run render` 不变。

> **「场景对齐」原理**：每段音频多长，对应场景就显示多久。画面与旁白共用同一条绝对时间轴，渲染逐帧 seek 时天然对齐，无需事后校准（因此不做逐字字幕）。

**A-4 三条铁律（务必遵守，`check` 会拦前两条）：**
- `<audio>` **必须有 `id`**，否则渲染器发现不了它 → **成片静音**
- 中文字体必须有 `@font-face { src: local("字体名") }`，否则 fallback 乱码
- 只用确定性逻辑：禁止 `Date.now()` / `Math.random()` / 网络 fetch

**A-5 校验**（必须 0 error 才能渲染）：

```bash
cd <hf-dir> && npm run check
```

**A-6 渲染出片**（直接产出带音频的 MP4）：

```bash
cd <hf-dir> && npm run render -- --fps 30 --quality high -o <work-dir>/output.mp4
```

hyperframes 路径到此**已出成片**，跳过 Step 6，直接 Step 7 交付。

#### 路径 B（fallback）— Playwright 录屏

无 Node 环境时用原有录屏方式，带 CSS 入场动画：

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py render \
  --json <work-dir>/slides.json \
  --work-dir <work-dir> \
  --mode video
```

**输出（video 模式）：** `<work-dir>/video/slide-01.webm`、`slide-02a.webm` ...

Playwright 会录制每页 HTML 的入场动画，录制时长 = 对应音频时长 + 0.8s。
也可用截图模式（无动画，速度快）：`--mode screenshot`，输出 PNG 到 `<work-dir>/slides/`。继续 Step 6 合成。

> Windows 若缺 headless shell，render 可走系统 Chrome（脚本已用 `channel="chrome"`）。

### Step 6 — 合成视频（仅路径 B 需要）

> 路径 A（hyperframes）已在 render 阶段出片，**无需本步**。

assemble 自动检测 `video/` 目录下的 WebM 文件。有 WebM 则使用视频模式合成（WebM + MP3 → clip），否则使用静态截图模式（PNG + MP3 → clip）。

```bash
python3 skills/knowledge-video/scripts/knowledge_video.py assemble \
  --work-dir <work-dir> \
  --output <work-dir>/output.mp4
```

可选参数：
- `--bg-music <path>` — 添加背景音乐（自动混音降低音量）
- `--bg-video <path>` — 背景视频（仅截图模式生效）

**输出：** `<work-dir>/output.mp4`

### Step 7 — 交付

告知用户：
1. 最终视频路径
2. 工作目录位置（方便查看中间产物或微调）
3. 如需调整某页，可修改 `slides.json` 后从 Step 4 重新执行

---

## 产物目录结构

```
<work-dir>/
├── slides.json              # 结构化脚本（你写的）
├── audio/slide-*.mp3        # 口播配音（两条路径都用）
├── html/slide-*.html        # 幻灯片 HTML 源文件（路径 B）
├── slides/slide-*.png       # 幻灯片截图（路径 B · screenshot 模式）
├── video/slide-*.webm       # 录屏视频（路径 B · video 模式）
├── clips/clip-*.mp4         # 单页视频片段（路径 B）
└── output.mp4               # 最终视频（两条路径最终都输出到这里）

<hf-dir>/                    # 路径 A（hyperframes）项目，与 work-dir 平级
├── index.html               # composition（照 references/hyperframes-composition.html 写）
├── assets/narration.mp3     # hf-prepare 拼接的连续旁白轨
└── timeline.json            # hf-prepare 生成的场景时间轴（start/duration + 文案）
```
