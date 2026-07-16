# Story JSON 字段契约

`story.json` 是 Agent 与 validator 之间的故事输入。文件必须是严格 JSON：双引号、无注释、无尾逗号。该契约只描述静音视觉，不包含音频字段。

## 目录

- 顶层字段
- Shot 字段
- Character 字段
- Prop 字段
- Bubble、Annotation、Caption
- Camera 与时间
- 枚举
- 镜头数量
- 简短示例

## 顶层字段

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `title` | string | 是 | 非空故事标题 |
| `aspect` | string | 是 | 固定为 `16:9` |
| `shots` | array | 是 | 非空、按播放顺序排列的镜头 |

validator 在 story 的任意层级禁止 `audio`, `bgm`, `music`, `voiceover`, `narration`, `sfx`。成片必须是纯静音；Agent 也不应把这些键藏入嵌套对象。

## Shot 字段

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `id` | string | 是 | 非空且全局唯一 |
| `duration` | number | 是 | 镜头时长，单位秒，必须有限且大于 0 |
| `pattern` | enum | 是 | 8 个 composition pattern 之一 |
| `character` | object | 否 | 单角色形式；不能与 `characters` 同时出现 |
| `characters` | array | 否 | 多角色形式，建议最多 2-3 个；不能与 `character` 同时出现 |
| `props` | array | 否 | 道具实例列表 |
| `bubble` | object | 否 | 单项气泡形式；不能与 `bubbles` 同时出现 |
| `bubbles` | array | 否 | 多项气泡形式；不能与 `bubble` 同时出现 |
| `annotation` | object | 否 | 单项批注形式；不能与 `annotations` 同时出现 |
| `annotations` | array | 否 | 多项批注形式；不能与 `annotation` 同时出现 |
| `caption` | string | 否 | 若提供，必须是非空中文静音字幕 |
| `camera` | object | 否 | 若提供，必须是 camera 对象 |

`duration` 管镜头边界。镜头内部对象使用 `at` 与 `dur`，不能用它们替代 shot 的 `duration`。推荐使用复数数组 `characters`、`bubbles`、`annotations` 表达可扩展输入；只有一个项目时可使用对应单数形式。

`character` 与 `characters` 不能同时出现；两者都可省略。`bubble` 与 `bubbles` 不能同时出现；`annotation` 与 `annotations` 不能同时出现。

## Character 字段

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `id` | string | 建议 | HTML 中稳定的角色标识 |
| `view` | enum | 否 | `front` 或 `side`，默认由 Agent 明确写出 |
| `action` | enum | 否 | 8 个动作之一 |
| `x` / `y` | number | 否 | hero frame 中角色的元素中心点坐标 |
| `scale` | number | 否 | 围绕元素中心点缩放的角色比例 |
| `at` | number | 否 | 相对当前 shot 起点的动作开始时间 |
| `dur` | number | 否 | 角色微动作持续时间 |

若使用角色，单数 `character` 与复数 `characters` 二选一。对象中的 `view`、`action`、`at`、`dur` 都是可选字段；提供时必须通过对应校验。`walk` 是 JSON action ID；HTML 调用资产时映射到 `microactions.walkCycle(...)`。正面与侧面角色必须用匹配的 spawn API。

## Prop 字段

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `id` | enum | 是 | 32 个 prop ID 之一 |
| `x` / `y` | number | 否 | hero frame 中道具的元素中心点坐标 |
| `scale` | number | 否 | 围绕元素中心点缩放的道具比例 |
| `at` | number | 否 | 入口开始时间 |
| `dur` | number | 否 | 入口持续时间 |
| `seed` | string | 否 | 确定性手绘 seed |

## Bubble、Annotation、Caption

### `bubble` / `bubbles`

`bubble` 表示单个对象，`bubbles` 表示对象数组，两者不能同时出现。推荐使用复数数组；单项 fixture 可保留 `bubble`。

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `text` | string | 否 | 若提供 `text`，必须是非空字符串；短句优先 |
| `at` | number | 否 | 出现时间 |
| `dur` | number | 否 | 屏幕停留时长 |
| `anchor` | string | 否 | 对应角色 id |

### `annotation` / `annotations`

`annotation` 表示单个对象，`annotations` 表示对象数组，两者不能同时出现。推荐使用复数数组；单项 fixture 可保留 `annotation`。

| 字段 | 类型 | 必需 | 契约 |
| --- | --- | --- | --- |
| `text` | string | 否 | 若提供 `text`，必须是非空字符串 |
| `color` | enum | 否 | `color` 可选；提供时只能是 `#e2483d`、`#f5a623` 或 `#2f7dd1` |
| `at` | number | 否 | 出现时间 |
| `dur` | number | 否 | 停留时长 |

### `caption`

`caption` 是可选的 shot 字符串字段，不是音频字幕轨。提供时必须非空，并在画面中自然换行，不使用 `<br>`，也不依赖语音或时间戳文件。

## Camera 与时间

`camera` 整体可选；若提供则必须是对象，可包含以下字段：

| 字段 | 类型 | 契约 |
| --- | --- | --- |
| `x` / `y` | number | camera 相对画布中心的位移，不是元素中心点 |
| `scale` | number | 轻微推近或拉远，默认 `1` |
| `at` | number | 相对 shot 起点的开始时间 |
| `dur` | number | camera tween 持续时间 |
| `ease` | string | 确定性 GSAP ease 名称 |

character/characters、props、bubble/bubbles、annotation/annotations、camera 中所有嵌套 `at` 必须是所属 shot 内的非负有限数。若提供 `dur`，它必须是正有限数，且 `at + dur` 不能越过该 shot 的 `duration`。只提供 `dur` 时 `at` 按 0 计算。时间以秒为单位，timeline 构建必须同步且可 seek。

## 枚举

### 8 个 pattern

`character-state`、`dialogue`、`journey`、`process`、`comparison`、`cause-effect`、`reveal`、`summary`

### 2 个 view

`front`、`side`

### 8 个 action

`idle`、`blink`、`wave`、`walk`、`nod`、`jump`、`think`、`surprise`

### 32 个 prop

| 类别 | ID |
| --- | --- |
| 办公 | `laptop`, `coffee`, `docs`, `calendar`, `phone`, `printer`, `badge`, `chair` |
| 流程 | `conveyor`, `funnel`, `scale`, `gate`, `blackbox`, `ladder`, `pipe`, `mailbox` |
| 反应 | `idea`, `question`, `excl`, `sweat`, `anger`, `zzz`, `boom`, `up` |
| 符号 | `arrow`, `fork`, `loop`, `check`, `cross`, `balance`, `gear`, `network` |

## 镜头数量

- 常规故事默认 4-8 shots。
- contract 测试和最小夹具允许 2-shot，用于快速验证完整链路。
- 2-shot 是测试下限，不是常规叙事默认值。

## 简短示例

```json
{
  "title": "小黑提交了申请",
  "aspect": "16:9",
  "shots": [
    {
      "id": "shot-1",
      "duration": 4.5,
      "pattern": "character-state",
      "character": {"id": "worker", "view": "front", "action": "wave", "at": 0.8, "dur": 1.0},
      "props": [{"id": "docs", "at": 0.4, "dur": 0.5}],
      "bubble": {"text": "提交。", "at": 1.1, "dur": 2.0},
      "annotation": {"text": "已进入流程", "color": "#2f7dd1", "at": 0.6, "dur": 2.5},
      "caption": "小黑认真提交了申请。",
      "camera": {"x": 0, "y": 0, "scale": 1, "at": 0.2, "dur": 0.6}
    }
  ]
}
```
