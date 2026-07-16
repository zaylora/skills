# RAG 科普短视频 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 本计划编排 `chengfeng-videocut-skills`(剪口播 + 口播成片)制作一条视频,不是写新代码。每个任务的"测试"是**可观察的验收动作**(ffprobe / 网页确认 / 抽关键帧),不是单元测试。

**Goal:** 把 [设计文档](../specs/2026-07-16-rag-explainer-video-design.md) 的 RAG 口播脚本,做成一条 1080×1440 逻辑画布、导出 1620×2160 的 3:4 竖屏成片。

**Architecture:** 用户按稿录制 `rag_raw.mp4` → `剪口播` 粗剪并产出剪后字幕 → `口播成片` 按 6 镜分镜生成 HTML 画面、时间线预览、最终 MP4。每个阶段都有人工确认门。

**Tech Stack:** Node.js 22、FFmpeg 7.1、火山引擎录音文件识别 2.0(Seed ASR)、chengfeng-videocut-skills、小黑风格 SVG/GSAP 动画。bash 脚本通过 Git Bash(Bash 工具)执行,`.cjs` 脚本用 `node` 执行。

## Global Constraints

- 画幅 `3:4`:逻辑画布 `1080×1440`,DPR `1.5`,导出 `1620×2160`,30fps。
- 动画风格 `xiaohei`(小黑漫画感 SVG)。图标必须从动画库索引取,已有的 ChatGPT/Claude 等图标不得用抽象形状替代。
- 受众为完全不懂技术的普通人:成片画面不出现代码、不出现素材路径/内部说明文字。
- 时长与剪后源视频一致(口播稿约 400 字,念读约 1.5 分钟)。
- **审核硬规则**:`剪口播` 到审核网页必须停下交用户点击「执行剪辑」,Agent 不擅自调 `/api/cut`;`口播成片` 必须先给分镜稿、再给时间线预览,两道确认门通过后才导出。
- **剪后字幕硬规则**:必须基于剪后视频重新转写(`video.raw.srt` 初稿),再由 Agent 对照口播稿 AI 校对成 `video.srt`;不能沿用原视频字幕,不能把火山初稿直接当最终字幕。
- **删前保后**:所有重复/口误,删前面那一遍,保留后面更完整的一遍。
- **Windows 兼容**:skill 里的 `ln -sf` 符号链接在 Git Bash 下可能失败;本计划一律用**文件复制**代替符号链接,产物不受影响。

## File Structure

项目根:`E:/github/skills/rag-video/`(本计划新建)

```
rag-video/
├── rag_raw.mp4                      # Task 1:用户录制的原始口播
├── assets/                          # 可选素材(本片以动画为主,通常为空)
├── output/
│   └── 2026-07-16_rag_raw/
│       ├── 剪口播/
│       │   ├── 1_转录/{audio.mp3, volcengine_result.json, subtitles_words.json}
│       │   ├── 2_分析/{readable.txt, sentences.txt, auto_selected.json, 口误分析.md}
│       │   └── 3_审核/{review.html, video.mp4(链接/副本), cut_done.json, rag_raw_cut.mp4}
│       └── 字幕/
│           ├── 1_转录/{audio.mp3, volcengine_result.json}
│           ├── subtitles_with_time.json
│           └── 3_输出/{video.raw.srt, video.srt}
├── source_cut.mp4                   # Task 3:剪后视频副本
├── subtitles.srt                    # Task 3:AI 校对后字幕副本
├── review/
│   ├── storyboard-audit-v1.html     # Task 4:分镜核对页
│   └── timeline-preview.html        # Task 5:时间线预览
├── html-modules/                    # Task 5:6 镜的 HTML/小黑动画模块 + render-mode.js
├── final-player.html                # Task 6:合成播放器
└── rag_成片.mp4                     # Task 6:最终交付
```

只读引用(不修改):`E:/github/skills/.claude/skills/chengfeng-videocut-skills/`
- 剪口播脚本:`.../剪口播/scripts/`
- 口播成片脚本:`.../口播成片/scripts/`(`.cjs`)
- 分镜/时间线模板:`.../口播成片/templates/`
- 动画风格:`.../口播成片/动画/ian-xiaohei-svg-motion/`

约定变量(执行时设定):
```bash
SKILL_ROOT="E:/github/skills/.claude/skills/chengfeng-videocut-skills"
PROJ="E:/github/skills/rag-video"
```

---

### Task 0: 环境与项目初始化

**Files:**
- Create: `E:/github/skills/rag-video/`(及 `assets/`)
- Create/Modify: `E:/github/skills/.claude/skills/chengfeng-videocut-skills/.env`

**Interfaces:**
- Produces: 可用的项目根目录 `$PROJ`;已配置的 `VOLCENGINE_API_KEY`。

- [ ] **Step 1: 创建项目目录**

```bash
mkdir -p "E:/github/skills/rag-video/assets"
```

- [ ] **Step 2: 复制 .env 模板**

```bash
cd "E:/github/skills/.claude/skills/chengfeng-videocut-skills" && cp .env.example .env
```

- [ ] **Step 3: 写入火山 API Key**

编辑 `.env`,把用户从[火山控制台](https://console.volcengine.com/speech/new/setting/activate?projectName=default)开通「录音文件识别 2.0」后拿到的 Key 填入:
```
VOLCENGINE_API_KEY=用户的真实key
```

- [ ] **Step 4(验收): 确认环境就绪**

```bash
node --version && ffmpeg -version | head -1 && grep -q "VOLCENGINE_API_KEY=..*" "E:/github/skills/.claude/skills/chengfeng-videocut-skills/.env" && echo "ENV OK"
```
Expected: 打印 Node 版本、FFmpeg 版本,末行 `ENV OK`。

---

### Task 1: 录制原始口播(用户执行,前置门)

**Files:**
- Create: `E:/github/skills/rag-video/rag_raw.mp4`

**Interfaces:**
- Consumes: 设计文档第 4 节「完整口播稿(连读版)」。
- Produces: `rag_raw.mp4`(含音频轨的口播录像;画面内容不限)。

- [ ] **Step 1: 按稿录制**

用户按设计文档口播稿念一遍,录成视频。念错当句从头重念(后续「删前保后」会删掉错的那遍);句间留短暂停顿。

- [ ] **Step 2: 放入项目目录并命名**

把录像保存为 `E:/github/skills/rag-video/rag_raw.mp4`。

- [ ] **Step 3(验收): 确认可用**

```bash
ffprobe -v error -show_entries format=duration:stream=codec_type -of default=noprint_wrappers=1 "file:E:/github/skills/rag-video/rag_raw.mp4"
```
Expected: 同时出现 `codec_type=video` 和 `codec_type=audio`;`duration` 约 80–110 秒。

---

### Task 2: 剪口播 · 转录分析与审核页(→ 用户确认门)

**Files:**
- Create: `output/2026-07-16_rag_raw/剪口播/{1_转录,2_分析,3_审核}/*`

**Interfaces:**
- Consumes: `rag_raw.mp4`(Task 1)。
- Produces: `subtitles_words.json`(字级时间轴)、`auto_selected.json`(预选删除 idx)、审核页 URL。

- [ ] **Step 1: 建目录并提取音频**

```bash
cd "$PROJ" && mkdir -p "output/2026-07-16_rag_raw/剪口播/1_转录" "output/2026-07-16_rag_raw/剪口播/2_分析" "output/2026-07-16_rag_raw/剪口播/3_审核"
ffmpeg -i "file:$PROJ/rag_raw.mp4" -vn -acodec libmp3lame -y "output/2026-07-16_rag_raw/剪口播/1_转录/audio.mp3"
```

- [ ] **Step 2: 火山转录**

```bash
cd "$PROJ/output/2026-07-16_rag_raw/剪口播/1_转录"
"$SKILL_ROOT/剪口播/scripts/volcengine_transcribe.sh" audio.mp3
```
Expected: 生成 `volcengine_result.json`(非空,含 `utterances`)。

- [ ] **Step 3: 生成字级时间轴**

```bash
node "$SKILL_ROOT/剪口播/scripts/generate_subtitles.js" volcengine_result.json
```
Expected: 生成 `subtitles_words.json`。

- [ ] **Step 4: 生成 readable.txt 与 sentences.txt,脚本标记静音,头尾裁剪**

按 `剪口播/SKILL.md` 步骤 5.1 / 5.3 / 5.4 / 5.4b 依次执行(生成易读文本、句子列表、`auto_selected.json` 静音预选、补尾元素)。

- [ ] **Step 5: AI 分析口误(并行三类)**

按 SKILL.md 步骤 5.5,派 A-句间重复 / B-句内重复 / C-残句 三个子任务读取 `sentences.txt`,合并要删的 idx 到 `auto_selected.json`(去重排序)。本片是照稿念的短口播,重点抓「RAG」念错重来、整句重说。高风险整句删除走复核。

- [ ] **Step 6: 生成审核页并启动服务**

```bash
cd "$PROJ/output/2026-07-16_rag_raw/剪口播/3_审核"
node "$SKILL_ROOT/剪口播/scripts/generate_review.js" ../1_转录/subtitles_words.json ../2_分析/auto_selected.json "$PROJ/rag_raw.mp4"
node "$SKILL_ROOT/剪口播/scripts/review_server.js" 8899 "$PROJ/rag_raw.mp4"
```
用后台任务托管 `review_server.js`(不要用 `python -m http.server`,视频依赖 HTTP Range)。

- [ ] **Step 7(验收 + 门): 交用户确认**

把 `http://localhost:8899` 交给用户。**在用户点击「执行剪辑」前,Agent 停在这里**,不调 `/api/cut`、不模拟点击。

---

### Task 3: 剪口播 · 剪后重转写与字幕校对(→ source_cut.mp4 + subtitles.srt)

**Files:**
- Create: `.../3_审核/rag_raw_cut.mp4`、`.../字幕/3_输出/{video.raw.srt, video.srt}`
- Create: `$PROJ/source_cut.mp4`、`$PROJ/subtitles.srt`

**Interfaces:**
- Consumes: 用户在审核页确认后由服务器写出的 `cut_done.json` 与剪后视频。
- Produces: `source_cut.mp4`(剪后视频)、`subtitles.srt`(AI 校对后字幕)——供 Task 4+ 使用。

- [ ] **Step 1: 监听剪后视频**

```bash
node "$SKILL_ROOT/剪口播/scripts/watch_cut_done.js" "$PROJ/output/2026-07-16_rag_raw/剪口播/3_审核"
```
Expected: 返回 JSON,含 `output`(剪后视频路径)、`newDuration`。把 `output` 记为 `CUT_VIDEO`。

- [ ] **Step 2: 基于剪后视频重新转写**

```bash
"$SKILL_ROOT/剪口播/scripts/generate_srt_for_video.sh" "$CUT_VIDEO" "$PROJ/output/2026-07-16_rag_raw/字幕"
```
Expected: 生成 `字幕/3_输出/video.raw.srt`(火山初稿)。

- [ ] **Step 3: AI 校对字幕**

读取 `video.raw.srt`,对照设计文档口播稿校对:保留时间轴,只改文字;把「RAG」「AI 幻觉」「私有资料」等术语改正确;修不合理断句;不新增没说的话。写入 `字幕/3_输出/video.srt`。

- [ ] **Step 4: 整理基础素材包(用复制,不用符号链接)**

```bash
cp "$CUT_VIDEO" "$PROJ/source_cut.mp4"
cp "$PROJ/output/2026-07-16_rag_raw/字幕/3_输出/video.srt" "$PROJ/subtitles.srt"
```

- [ ] **Step 5(验收): 核对素材包**

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "file:$PROJ/source_cut.mp4"
head -20 "$PROJ/subtitles.srt"
```
Expected: 剪后 `duration` 比原始略短(删了口误/静音);字幕首段文字与口播稿开头一致,时间轴从 0 附近开始。

---

### Task 4: 口播成片 · 分镜稿(→ 用户确认方向门)

**Files:**
- Create: `$PROJ/review/storyboard-audit-v1.html`
- Read: `$SKILL_ROOT/口播成片/{SKILL.md, templates/storyboard-audit.html, 用户配置/default.json}`

**Interfaces:**
- Consumes: `source_cut.mp4`、`subtitles.srt`、设计文档 6 镜分镜。
- Produces: 分镜核对 HTML(6 段,对应设计文档镜头 1–6)。

- [ ] **Step 1: 读用户配置与模板**

确认 `用户配置/default.json` 为 `{"aspectRatio":"3:4","animationStyle":"xiaohei"}`(若不是,本项目内用 `--ratio 3:4` 覆盖,不改全局默认)。基于 `templates/storyboard-audit.html` 起页面。

- [ ] **Step 2: 按 6 镜写分镜段**

把设计文档 6 个镜头逐段落进分镜稿。每段写清:时间范围、字幕编号、完整口播、画面任务、画面类型(全部为 `HTML 动画` 或 `文字+动画`)、镜头动作。一页只讲一个概念(镜头 4 三步流程可在一页内分三阶段显隐)。

- [ ] **Step 3: 生成并打开分镜稿**

用支持 HTTP Range 的服务打开:
```bash
node "$SKILL_ROOT/口播成片/scripts/serve_range_preview.cjs" --project-dir "$PROJ" --port 8767
```

- [ ] **Step 4(验收 + 门): 交用户确认方向**

用户回答每段「这句话说到这里,观众该看到什么」。**方向确认前不进入时间线预览。**

---

### Task 5: 口播成片 · 时间线预览与动画模块(→ 用户确认门)

**Files:**
- Create: `$PROJ/html-modules/module-*.html`、`xiaohei-*.html`、`render-mode.js`
- Create: `$PROJ/review/timeline-preview.html`
- Read: `$SKILL_ROOT/口播成片/{templates/timeline-preview.html, 动画/ian-xiaohei-svg-motion/**, references/artifact-contracts.md}`

**Interfaces:**
- Consumes: 已确认的分镜稿、`source_cut.mp4`、`subtitles.srt`。
- Produces: 各镜 HTML 动画模块 + 时间线预览页,画面与口播逐句对齐。

- [ ] **Step 1: 实现各镜动画模块**

按小黑风格实现:考场/闭卷牌(镜头 2)、闭卷↔开卷翻转(镜头 3)、三步流程+图书管理员抽页(镜头 4)、三对勾+闭卷vs开卷对比(镜头 5)、结束卡(镜头 6)。每个动作绑定到具体口播句;多阶段模块显式管理显隐(下一阶段出现时上一阶段说明卡隐藏)。图标从动画库索引取。

- [ ] **Step 2: 注入 render mode**

```bash
node "$SKILL_ROOT/口播成片/scripts/write_render_mode.cjs" --project-dir "$PROJ"
```
确认 HTML 模块 URL 带 `?timeline=1&render=1`。

- [ ] **Step 3: 生成时间线预览并打开**

基于 `templates/timeline-preview.html` 生成 `review/timeline-preview.html`,用上面的 `serve_range_preview.cjs`(8767)打开。

- [ ] **Step 4(验收 + 门): 逐项检查**

确认:画面切换跟口播句对齐;竖屏内无挡字/裁切/黑边;左右分布元素未被裁掉(抽左右边界帧,不只看中心);多阶段显隐正确。交用户确认。**确认前不合成。**

---

### Task 6: 口播成片 · 合成导出与验收(→ 最终 MP4)

**Files:**
- Create: `$PROJ/final-player.html`、`$PROJ/rag_成片.mp4`
- Read: `$SKILL_ROOT/口播成片/references/artifact-contracts.md`

**Interfaces:**
- Consumes: 已确认的时间线预览、所有 HTML 模块、`source_cut.mp4`。
- Produces: `rag_成片.mp4`(1620×2160,3:4,含音频)。

- [ ] **Step 1: 确认 final-player 与预览同一渲染上下文**

新写 `final-player.html` 前读 `artifact-contracts.md`;确保逻辑画布与预览相同(1080×1440),不用 CSS 缩放放大画布。

- [ ] **Step 2: 高清导出**

先取剪后时长:
```bash
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "file:$PROJ/source_cut.mp4")
node "$SKILL_ROOT/口播成片/scripts/export_final_video.cjs" --project-dir "$PROJ" --input-video "$PROJ/source_cut.mp4" --duration "$DUR" --ratio 3:4 --dpr 1.5 --frame-format png --crf 14 --preset slow
```

- [ ] **Step 3(验收 A): ffprobe 检查**

```bash
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of default=noprint_wrappers=1 "file:$PROJ/rag_成片.mp4"
```
Expected: `width=1620 height=2160`;帧率约 30;有 `codec_type=audio`;`duration` ≈ `source_cut.mp4`。

- [ ] **Step 4(验收 B): 抽关键帧核对**

对镜头 2、4、5 各抽 1 张对应口播时间点的帧,和时间线预览同一时间点对照,大小/位置/裁切/显隐一致。画面无 HUD、按钮、浏览器 UI、素材路径文字。

- [ ] **Step 5: 交付**

把 `rag_成片.mp4` 路径交给用户,附一句时长/分辨率确认。

---

## Self-Review(计划自查)

**Spec 覆盖:**
- 概述(画幅/时长/形式)→ Global Constraints + Task 6 验收 ✅
- 核心比喻/一句话主张 → Task 4/5 分镜与动画 ✅
- 6 镜分镜脚本 → Task 4 Step 2、Task 5 Step 1 ✅
- 完整口播稿 → Task 1(录制)、Task 3 Step 3(字幕校对对照) ✅
- 录制指导 → Task 1 ✅
- 后续流程(剪口播→成片→验收)→ Task 2/3/5/6 ✅
- 交付物清单 → 各 Task 产物 ✅
- 前提/风险(火山 Key、Windows 符号链接、审核硬规则)→ Task 0、Global Constraints ✅

**占位符扫描:** 无 TBD/TODO;凡引用 skill 步骤处均给出实际命令与本机路径。

**一致性:** 变量 `$SKILL_ROOT`/`$PROJ`/`$CUT_VIDEO`/`$DUR` 全程一致;`source_cut.mp4`、`subtitles.srt` 命名前后统一;用复制替代符号链接的策略贯穿 Task 3。
