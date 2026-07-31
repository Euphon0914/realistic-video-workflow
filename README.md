# Realistic Video Workflow

[中文](#中文) · [English](#english)

## 中文

`run-realistic-video-workflow` 是一套资料驱动、可恢复、人工审核介入的 Codex Skill，用于制作真人质感写实视频。它不预设项目类型，可用于纪录片、人物故事、品牌或产品片、文化旅游、教育科普、公益内容、活动短片和社交视频。

用户只需提交已有资料并说“启动”或“继续写实人物视频工作流”。Skill 会自行整理资料、推导需求、维护状态并推进制作，只在五个固定闸门或真正影响事实、授权、成本和已批准设计的异常处暂停。

### 固定基线

- 真实皮肤、五官、人体结构、表情、服装和运动惯性；
- 符合真实摄影的焦段、景深、机位、光线、材质和声音；
- 克制调色与特效，避免塑料皮肤、游戏 CG 感和无依据科幻光；
- 项目类型、地域、品牌、时长、语言、画幅和模型设置均从新资料重新推导。

### 五个审核闸门

1. 项目简报；
2. 脚本与叙事；
3. 人物、物件与视觉资产；
4. 分镜、生成计划、提示词—参考图审计及生产授权；
5. 成片与归档。

### 需要提交的资料

可以直接提交未整理的文件，包括项目背景、人物照片与授权、产品或物件资料、场地照片、采访、脚本、研究资料、品牌规范、参考影片、合规要求和交付规格。资料缺失时，Skill 先从现有文件推导，只把会改变结果的少量问题集中到 Gate 1。

### 可获得的资料

项目简报、事实与授权风险表、脚本、旁白、字幕、角色板、资产约束卡、视觉圣经、分镜、复用矩阵、生成提示词、引用职责表、提示词—参考图审计、生成任务记录、视频 QA、成片和完整归档包。

### 安装

在 Codex 中使用系统自带的 `$skill-installer`：

```text
Install the skill from:
https://github.com/Euphon0914/realistic-video-workflow/tree/main/skills/run-realistic-video-workflow
```

也可以使用安装脚本：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo Euphon0914/realistic-video-workflow \
  --path skills/run-realistic-video-workflow
```

安装后在下一轮对话中调用：

```text
Use $run-realistic-video-workflow to inspect these materials and start the project.
```

### 核心命令

要求 Python 3.10+，只使用标准库。

```bash
python skills/run-realistic-video-workflow/scripts/init_project.py PROJECT_DIR --source MATERIALS_DIR
python skills/run-realistic-video-workflow/scripts/update_state.py PROJECT_DIR set --stage intake_brief --status needs_review --artifact 01_brief/project-brief.md --pending-question "Confirm the delivery runtime"
python skills/run-realistic-video-workflow/scripts/update_state.py PROJECT_DIR set --stage storyboard_generation_audit --status needs_review --artifact 05_storyboards/shot-01.md --depends-on 03_locked-assets/lead-character.md
python skills/run-realistic-video-workflow/scripts/update_state.py PROJECT_DIR invalidate --artifact 03_locked-assets/lead-character.md --reason "character asset revised"
python skills/run-realistic-video-workflow/scripts/validate_project.py PROJECT_DIR
```

所有命令将机器可读 JSON 写入标准输出；成功退出码为 `0`，验证或执行错误为 `1`，命令行用法错误由 `argparse` 返回 `2`。

### 可选集成

核心状态机不依赖任何生成服务。生图、画布编排和视频提示词能力仅在相应阶段按需检测；缺失时，上游工作仍会继续。详见 [`integrations.md`](skills/run-realistic-video-workflow/references/integrations.md)。

### 隐私

不要把真实项目资料、肖像、客户文件、生成服务凭据或运行中的项目目录提交到此仓库。初始化器默认不会把源资料的绝对本机路径写入 manifest，也会跳过常见凭据、缓存、符号链接和过大文件。

## English

`run-realistic-video-workflow` is a material-driven, resumable Codex Skill for human-in-the-loop production of photorealistic live-action video. It supports documentaries, portraits, brand and product stories, cultural, travel, educational, public-interest, event, and social video without assuming a fixed project type.

Upload the available materials and ask the Skill to start or resume. It organizes evidence, derives project-specific requirements, persists decisions, and advances independently. It pauses at five review gates: brief, script, locked visual assets, pre-production authorization, and final delivery.

The core workflow uses Python 3.10+ and the standard library only. Image generation, canvas orchestration, and model-specific prompting are optional integrations detected only when needed.

Install with `$skill-installer` from:

```text
https://github.com/Euphon0914/realistic-video-workflow/tree/main/skills/run-realistic-video-workflow
```

Then invoke it on the next turn:

```text
Use $run-realistic-video-workflow to inspect these materials and start the project.
```

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q skills/run-realistic-video-workflow/scripts
```

The repository version is the source of truth. Do not develop against a copied installation under `$CODEX_HOME/skills`.

## License

[MIT](LICENSE)
