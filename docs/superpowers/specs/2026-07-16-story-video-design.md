# story-video Skill 设计文档

**日期**：2026-07-16
**状态**：已通过 brainstorming，待实施

## 目标

一个 Agent 引导式 skill，产出**小黑手绘风格的 16:9 故事动画 MP4**。用户给出故事主题，Agent 当导演把主题拆成分镜、组装小黑场景、编排动画，产出与 [ian-xiaohei-illustrations](https://github.com/helloianneo/ian-xiaohei-illustrations) 风格一致的静音故事视频。

渲染基于 [hyperframes](https://github.com/heygen-com/hyperframes)（Write HTML → Render video）。

## 核心决策

经 brainstorming 确认的地基决策：

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 画面技术路线 | **纯 SVG 矢量组件库** | 风格 100% 一致、矢量无损、确定性渲染、零 API 成本、可做真正的角色动画 |
| 动画深度 | **角色部件动画** | 小黑拆成可动部件（身体/双眼/双臂/双腿），预设微动作库；比"会动的插画"有生命力，又不像完整骨骼那样过重 |
| 叙事与声音 | **纯视觉 + 文字，完全静音** | 保留对白气泡和字幕文字，但不配音、无 BGM。观众靠"看字+看动画"理解故事 |
| 画幅 | **16:9 横版** | 1920×1080，适合横屏叙事平台；复用现成渲染配置 |
| 角色组件化 | **单一 SVG + 命名部件 + GSAP 微动作库** | SVG `<g>` 关节点可精确控制，纯文本 AI 可读写，与 hyperframes 的 GSAP 适配器天生契合 |
| 视图变体 | **正面 + 侧面** | 正面用于对话/待机，侧面用于行走（有方向感）；镜像翻转即可左右互换 |

## 架构

### 定位

`story-video` 是 **Agent 引导式 skill**：Agent 当导演（负责分镜、组装场景、编排动画），代码资产库当工具人（提供角色/物品/动画的可复用代码）。

### 与 knowledge-video 的复用关系

仓库已有 [knowledge-video](../../../skills/knowledge-video/SKILL.md) skill，打通了 hyperframes 渲染骨架。去掉配音/BGM 后，`story-video` 对它的依赖仅剩 **hyperframes 渲染模式的组织方式**（composition 骨架写法、`window.__timelines` 注册、`npm run check`/`render` 流程）。TTS 和 assemble 混音步骤**不使用**。

### 数据流

```
故事主题
  → [Agent] 故事构思 + 分镜脚本 story.json（角色/物品/气泡文字/批注/镜头/时长）
  → [Agent] 按 story.json + 资产库，写出 hyperframes 的 index.html（组装五层，纯视觉）
  → [hyperframes] npm run check → render → 逐帧 MP4（静音）
  → output.mp4（完成，无需 assemble 混音步骤）
```

### 五层场景模型

每个镜头（shot）由五层组合而成：

1. **角色层** `characters` — 小黑（正面/侧面），调用微动作库
2. **物品层** `props` — 打工人物品等纯黑描边矢量资产
3. **气泡层** `bubbles` — 对白气泡文字（纯显示，不配音）
4. **批注层** `annotations` — 红/橙/蓝手写批注
5. **镜头层** `camera` — 推拉摇等运镜，作用于整个 camera 层

## 目录结构

```
skills/story-video/
├── SKILL.md                          # Agent 引导流程（导演手册）
├── references/
│   ├── xiaohei-ip.md                 # 小黑 IP 规范：形象定义、气质、什么能改什么不能
│   ├── style-dna.md                  # 风格 DNA：细线2.2px、手绘抖动、纯白底、红橙蓝批注
│   ├── composition-patterns.md       # 8 种构图模式（源自原作）
│   ├── scene-composition.html        # 五层场景骨架参考模板
│   └── story-json-schema.md          # story.json 字段规范 + 完整示例
├── assets/
│   ├── handdraw.js                   # 手绘引擎：hLine/hPoly/hEllipse（确定性抖动）
│   ├── xiaohei.js                    # 小黑角色：正面+侧面 SVG 模板 + spawn 函数
│   ├── microactions.js               # 微动作库：blink/wave/walkCycle/nod/jump/think/surprise…
│   └── props.js                      # 打工人物品库：4类32+ 资产，按 id 取用
└── scripts/
    └── story_video.py                # （可选）薄封装，仅在需要脚本辅助时使用
```

**组织原则**：
- `references/` 是"喂给 AI 的知识"（Markdown 规范），`assets/` 是"AI 调用的代码"（可执行 JS）。职责分离。
- 资产是 JS 模块不是图片。Agent 写 composition 时用 `<script src>` 引入，调用函数生成 SVG、编排动画。风格一致、可组合、AI 可读写。
- `assets/` 先平铺，暂不细分子目录。

## 组件设计

### handdraw.js — 手绘引擎

确定性伪随机（seed 可控，满足 hyperframes 确定性要求）驱动的手绘线条生成器：

- `hLine(x1,y1,x2,y2,opts)` — 手绘线段：折线化 + 中段垂直扰动 + 端点过冲
- `hPoly(points,opts)` — 手绘多段线/多边形（可闭合）
- `hEllipse(cx,cy,rx,ry,opts)` — 手绘椭圆：极坐标采样 + 半径抖动 + 不完全闭合
- 线条规范：细线（默认 2.2px）、圆角端点、松弛不机械

### xiaohei.js — 小黑角色

- 正面 SVG 模板：`body` + 双眼（`eye-l`/`eye-r`）+ 双臂（`arm-l`/`arm-r`）+ 双腿（`leg-l`/`leg-r`），每部件带 class 和关节点
- 侧面 SVG 模板：面朝右，前后腿（`leg-f`/`leg-b`）、前后臂（`arm-f`/`arm-b`）、单眼；镜像翻转（`scaleX:-1`）即可朝左
- `spawn(id)` / `spawnSide(id)` — 把模板注入指定容器，返回 GSAP selector

### microactions.js — 微动作库

复用 GSAP 编排的预设动作，Agent 传角色 selector 调用：

- `idle` — 待机：呼吸起伏 + 定时眨眼
- `blink` — 眨眼
- `wave` — 挥手（臂绕肩摆动）
- `walkCycle` — 走路（侧面：前后腿/臂绕关节反相摆动 + 身体 bob + 横向位移）
- `nod` — 点头（**2D 方案**：整体下沉 + 身体纵向压扁，锚在脚底。SVG `<g>` 不支持 3D rotationX）
- `jump` — 跳跃（上下 + 落地挤压）
- `think` — 思考（抬手到脸侧 + 身体微倾 + 浮现符号）
- `surprise` — 惊讶（眼睛放大 + 小跳 + 双臂张开）

### props.js — 打工人物品库

4 类 32+ 资产，全部用 handdraw.js 绘制，风格统一。按 id 取用：

- **① 打工日常物品**：laptop / coffee / docs / calendar / phone / printer / badge / chair
- **② 低科技隐喻**（原作物件池）：conveyor / funnel / scale / gate / blackbox / ladder / pipe / mailbox
- **③ 打工情绪状态**：idea / question / excl / sweat / anger / zzz / boom / up
- **④ 抽象动作**：arrow / fork / loop / check / cross / balance / gear / network

## story.json 数据结构

Agent 与渲染之间的核心契约。以分镜（shot）数组为中枢：

```jsonc
{
  "title": "小黑的周一早晨",
  "aspect": "16:9",
  "shots": [
    {
      "id": "s1",
      "duration": 5,                 // 显式秒数（无配音，时长自定）
      "pattern": "character-state",  // 构图模式（8选1）
      "caption": "周一早晨，小黑准时坐到工位上。",   // 屏底字幕（可选，纯显示）
      "characters": [
        { "role": "hero", "view": "front", "x": "20%", "action": "idle" }
      ],
      "props": [
        { "id": "laptop", "x": "50%", "y": "60%", "scale": 1 },
        { "id": "coffee", "x": "68%", "y": "62%" }
      ],
      "bubbles": [
        { "by": "hero", "text": "新的一周，加油。", "at": 1.5, "dur": 2.5 }
      ],
      "annotations": [
        { "text": "又是周一", "color": "red", "x": "40%", "y": "20%", "at": 2 }
      ],
      "camera": { "move": "zoom-in", "target": "50% 60%", "at": 3 }
    }
  ]
}
```

**字段说明**：
- `duration` — 每个 shot 显式秒数。root 总时长 = 各 shot 之和。
- `pattern` — 引导构图的模式名，配合 `composition-patterns.md`。
- `action` — 映射微动作库动作名。可用值：`idle`/`blink`/`wave`/`walk`/`nod`/`jump`/`think`/`surprise`。其中 `walk` 对应 `walkCycle()`，其余同名。渲染时由一个动作名→函数的分发表统一处理。
- `bubbles` / `annotations` 的 `at`（出现时刻）、`dur`（持续时长）控制节奏。
- `caption` — 可选屏底字幕。
- 所有文字均为纯显示，无配音。

## Agent 工作流程（SKILL.md 主体）

1. **明确故事需求** — 提取主题、核心表达、大致时长、镜头数偏好。确定工作目录 `out/<主题简称>-story/`。
2. **故事构思与分镜** — 拆成 4-8 个镜头的故事线（起承转合），每镜头选一种 pattern，读 `composition-patterns.md` 和 `xiaohei-ip.md` 保证不跑偏。
3. **写 story.json** — 分镜写成结构化 JSON，保存到工作目录。
4. **组装 hyperframes composition** — 照 `scene-composition.html` 骨架写 `index.html`：引入资产 JS → 遍历 shots 生成 `<div class="clip scene">`（data-start/data-duration 按累积秒数）→ 每 shot 内组装五层 + GSAP 编排 → 注册到 `window.__timelines`。
5. **校验与渲染** — `npm run check`（0 error）→ `npm run render` → 静音 MP4。
6. **交付** — 告知 MP4 路径、工作目录、如何微调（改 story.json 后从 Step 4 重跑）。

**核心原则**：Agent 主导创意（Step 2-4），代码只管渲染（Step 5）。

## 错误处理

1. **`npm run check` 是硬门槛** — 0 error 才能渲染。常见错误：动画没注册到 `window.__timelines`、用了非确定性逻辑（`Date.now()`/`Math.random()`/网络请求）。手绘引擎的伪随机必须 seed 确定性。
2. **中文字体** — 字幕/气泡/批注的中文，`@font-face` 用 `local()` 声明系统字体，否则渲染乱码。
3. **资产 JS 引入路径** — composition 的 `<script src>` 用相对路径正确指向 `assets/*.js`。
4. **环境缺失** — 无 Node.js 22+ 时提示安装；首次 `npx hyperframes browser ensure` 备好渲染 Chrome。

## 测试策略

1. **资产库单元验证** — 一个 `assets-preview.html` 渲染所有小黑视图、微动作、物品，人眼校验风格一致（本身即回归测试工具）。
2. **最小 story.json 冒烟测试** — 一个 2-shot 示例，跑通完整管线（组装→check→render→出 MP4），验证端到端不崩。
3. **确定性验证** — 同一 story.json 渲染两次，产物 MP4 应一致。

## 边界（YAGNI）

明确**不做**：

- ❌ 配音 / BGM（纯静音）
- ❌ 9:16 竖版（只 16:9）
- ❌ AI 文生图（纯 SVG）
- ❌ 背面视图（只正面 + 侧面）
- ❌ 完整骨骼系统（只部件级微动作）
- ❌ 真人 / 复杂多角色群戏（小黑为主，最多 2-3 个小黑同框）

## 成功标准

用户给一个故事主题，skill 能产出一个 4-8 镜头、小黑手绘风格、有角色动画 + 物品 + 气泡 + 批注 + 运镜的**静音 16:9 MP4**，风格与原作一致。
