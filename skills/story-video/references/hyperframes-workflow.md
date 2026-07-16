# Story Video 的 HyperFrames 独立工作流

本文件从空目录开始，完整说明如何把 `story.json` 变成静音 HyperFrames 成片。它不依赖、也不引用任何兄弟 skill。

## 目录

- 环境要求
- 初始化项目
- 校验并准备素材
- Agent 改写 composition
- HyperFrames 质量门
- Composition 硬约束
- 故障处理

## 环境要求

- Node.js >= 22
- FFmpeg 可在命令行调用
- `npx hyperframes` 可运行
- Python 3 可运行 `<skill-dir>/scripts/story_video.py`

先确认环境：

```powershell
node --version
ffmpeg -version
npx hyperframes doctor
npx hyperframes browser
```

`doctor` 检查 Node、FFmpeg、Chrome 与内存；`browser` 安装或管理 HyperFrames 使用的浏览器。环境检查失败时先修环境，不开始写 composition。

## 初始化项目

在希望放置成片工程的父目录执行：

```powershell
npx hyperframes init <project-name> --example blank --non-interactive
```

必须使用 blank 模板与 `--non-interactive`，避免 Agent 工作流等待交互输入。初始化后进入项目目录。

## 校验并准备素材

先校验严格 JSON，再准备四个本地资产、story 副本和 starter：

```powershell
python <skill-dir>/scripts/story_video.py validate <story.json>
python <skill-dir>/scripts/story_video.py prepare <story.json> <project-dir>
```

`prepare` 会把资产放入 `<project-dir>/assets/story-video/`。若 `<project-dir>/index.html` 已存在，它不会覆盖；Agent 必须继续按已校验 story 主动改写 `index.html`，不能把 starter 当最终成片。

## Agent 改写 composition

1. 读取 story 的 shot 顺序、`duration`、pattern 和固定文案。
2. 每个 shot 先用静态 HTML/CSS 建立 hero frame。
3. 在 camera 内放 character、props、bubble、annotation 四层；caption 可放 camera 内或外，但必须清楚分区。
4. 调用本地 `StoryVideo.xiaohei`、`StoryVideo.props` 和 `StoryVideo.microactions`，不重画同类资产。
5. 添加 `tl.from()` 入口、镜头内动作和场景 transition。
6. 保持纯静音：不创建 audio、BGM、旁白或音效轨。

## HyperFrames 质量门

HyperFrames 0.7.60 的主流程顺序不可颠倒：lint -> check -> preview -> render。

```powershell
npx hyperframes lint
npx hyperframes check
npx hyperframes preview --port <port>
npx hyperframes render --output final.mp4
```

`validate` 与 `inspect` 仅用于兼容旧版本，不作为主流程。0.7.60 使用 `check` 完成 composition、布局与渲染前检查。

preview 启动后交付 Studio URL，而不是直接打开源文件：

```text
http://localhost:<port>/#project/<project-name>
```

修复 lint 与 check 报告的错误和文字溢出后再 preview、render。只有最终 MP4 成功生成才算完成。

## Composition 硬约束

### Root 与 data 属性

- standalone `index.html` 的 body 直接包含唯一 root，不使用 `<template>` 包裹。
- 只有 root 拥有 `data-composition-id="main"`、`data-width="1920"`、`data-height="1080"`、`data-start="0"` 和 `data-duration`。
- scene div 不使用 `class="clip"`，也不重复 composition 或 timing data 属性。
- scene 1 默认可见；scene 2 及后续 scene 的容器初始 `opacity: 0`。

### Timeline

```javascript
window.__timelines = window.__timelines || {};
var tl = gsap.timeline({ paused: true });
window.__timelines.main = tl;
```

- timeline 必须 `paused: true` 并同步注册到 `window.__timelines.main`。
- 总时长来自 root 的 `data-duration`，不创建空 tween 撑时长。
- 首个入口在 0.1-0.3 秒，所有场景元素用 `tl.from()` 从入口态进入静态 CSS hero frame。
- 只动画视觉属性，优先 transform 与 opacity。

### 场景可见性与 transition

- 多镜头必须有 transition，不能跳切。
- 中等节奏解释视频优先使用 0.3-0.5 秒 CSS push transition。
- transition 同时把旧 scene 推出并把新 scene 推入；它就是旧 scene 的退出。
- 非最后 scene 禁止额外 exit tween，transition 开始时旧 scene 内容应完整可见。
- 最后 scene 可整体淡出，但不是必需。

### 确定性与有限循环

- 禁止 `Math.random`、`Date.now` 或基于当前时间的分支。
- 禁止 `repeat: -1`。需要循环时根据总持续时间计算 finite repeat，或直接给出有限 repeat 次数。
- 禁止在 `async`、`setTimeout`、`Promise` 或任何延迟回调中创建 timeline。
- 禁止 `<br>` 强制断行；让文本在固定宽度内自然换行。
- 不调用媒体的 play、pause 或 seek；本工作流本身不包含媒体轨。

## 故障处理

- CLI 或 render 找不到浏览器：重跑 `npx hyperframes doctor`，再运行 `npx hyperframes browser`。
- check 报文字溢出：先增加容器宽度或调整自然换行，再考虑减小字号；正文仍不能小于 20px。
- transition 前画面变空：删除旧 scene 内容上的退出 tween，只保留 scene 容器的 push。
- 捕获画面与浏览器不同：检查是否存在异步 timeline、无限 repeat 或非确定性逻辑。
- prepare 没覆盖 `index.html`：这是预期行为，Agent 应编辑现有 composition，而不是删除项目重来。
