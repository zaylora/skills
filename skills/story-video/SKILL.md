---
name: story-video
description: Use when 用户需要把故事主题、叙事脚本或分镜制作成小黑手绘风格的静音 16:9 动画视频。
---

# 故事视频

这是一个独立的故事视频制作技能。始终输出静音 16:9 动画，由 Agent 主导叙事、分镜、构图、动效与验证决策。

## 工作流

先解析已安装技能的根目录，记为 `<skill-dir>`。后续命令不得依赖当前工作目录恰好是技能根目录。

1. 根据主题编写 `story.json`，保持镜头目的清晰、节奏连贯。
2. 按需读取 `references/`：设计故事数据时查阅规格说明，组合场景时查阅 HTML 模板，处理绘制、角色、微动效或道具时查阅对应参考。
3. 在生成项目前校验故事：

   ```powershell
   python <skill-dir>/scripts/story_video.py validate story.json
   ```

4. 准备项目；该命令复制故事、运行时资产，并在项目没有 `index.html` 时加入场景模板：

   ```powershell
   python <skill-dir>/scripts/story_video.py prepare story.json <project-dir>
   ```

5. 由 Agent 根据每个镜头的叙事意图实现画面和时间线，不依赖旁白或音频传递信息。

## 参考资料路由

- 约束小黑角色设定时，读取 `references/xiaohei-ip.md`。
- 确认线条、色彩和动效风格时，读取 `references/style-dna.md`。
- 选择镜头构图模式时，读取 `references/composition-patterns.md`。
- 编写或校对故事 JSON 时，读取 `references/story-json-schema.md`。
- 执行 HyperFrames 工作流时，读取 `references/hyperframes-workflow.md`。
- 实现场景布局时，读取 `references/scene-composition.html`。
- 选用绘制、角色、微动效或道具资产时，读取 `references/assets-preview.html`。

不要一次性加载全部参考资料。

## 质量硬门

交付前必须依次执行：

```powershell
npx hyperframes lint <project-dir>
npx hyperframes check <project-dir>
npx hyperframes preview <project-dir>
npx hyperframes render <project-dir>
```

preview 必须人工审阅画面、时序和文字可读性，通过后才能执行 `render`。任一步失败都要修复并从失败步骤重新验证；没有成功渲染的成片不得交付。

`validate/inspect` 仅用于旧版兼容，不作为主流程命令。
