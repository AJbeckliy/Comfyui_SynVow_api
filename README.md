# Comfyui_SynVow_api

ComfyUI custom nodes for [SynVow](https://service.synvow.com) API integration.

ComfyUI 用于 SynVow API 集成的自定义节点。

---

## Supported Models 支持的模型

| Node 节点 | Model | Description 描述 |
|-----------|-------|-----------------|
| SynVow Sora2 视频生成 | sora-2 | OpenAI Sora2 image-to-video (10/15s) / OpenAI Sora2 图像转视频（10/15 秒） |
| SynVow Sora2 优质视频生成 | sora2-优质 | OpenAI Sora2 Pro image-to-video (4/8/12s) / 优质模式（4/8/12 秒） |
| SynVow Sora2 批量视频生成 | sora-2 | Batch version / 批量版本 |
| SynVow Sora2 优质批量视频生成 | sora2-优质 | Batch Pro version / 优质批量版本 |
| SynVow Veo3.1 视频生成 | veo3.1 | Google Veo3.1 text/image-to-video / 文生视频·图生视频 |
| SynVow Veo3.1 批量视频生成 | veo3.1 | Batch version / 批量版本 |
| SynVow Grok 视频生成 | grok-* | xAI Grok image-to-video / 图生视频 |
| SynVow Grok 批量视频生成 | grok-* | Batch version / 批量版本 |
| SynVow Gemini API 图生文 | gemini-* | Google Gemini multimodal text output / 多模态文本输出 |
| SynVow Gemini 提示词生成 | gemini-* | Prompt generation via Gemini / 提示词生成 |
| SynVow NanoBanana Pro 图像生成 | nanobanana | Image generation (T2I / I2I) / 文生图·图生图 |
| SynVow NanoBanana Pro 批量出图 | nanobanana | Batch image generation / 批量出图 |
| SynVow Nano2 图像生成 | nano2 | Nano2 image generation (T2I / I2I) / 文生图·图生图 |
| SynVow Nano2 批量出图 | nano2 | Batch version / 批量版本 |
| SynVow 文本分割 | — | Split text by delimiter, output text + list / 按分隔符切分文本，输出单条与列表 |
| SynVow GPT-Image-2 | gpt-image-2-文生图-默认 / gpt-image-2-图生图-默认 | GPT-Image-2 text-to-image & image-to-image / 文生图·图生图 |
| 🛒 电商详情页提示词生成器 | gemini-* | Multi-screen e-commerce detail page prompt generator with product & style reference images / 多屏电商详情页提示词生成，支持产品参考图与风格参考图 |
| 提示词文本编辑器 | — | Interactive text list editor in workflow / 工作流内交互式文本列表编辑器 |

---

## Installation 安装

1. Clone this repo into your ComfyUI `custom_nodes` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/AJbeckliy/Comfyui_SynVow_api.git
   ```

2. Restart ComfyUI.
3. Log in with your SynVow account via the menu bar (SynVow icon).

---

## Requirements 依赖

- Python `requests`, `aiohttp` (usually already available in ComfyUI environment)
- A [SynVow](https://service.synvow.com) account with API access / 需要 SynVow 账号及 API 权限

---

## Usage 使用方法

1. Click the SynVow icon in the ComfyUI menu bar to log in. / 点击菜单栏 SynVow 图标登录。
2. Add any SynVow node to your workflow. / 将节点添加到工作流。
3. Connect inputs and run. Videos/images are saved to the configured output path. / 连接输入并运行，视频/图片保存到配置的输出路径。

---

## 更新日志

### 2026-05-09
- **新增 `🛒 电商详情页提示词生成器` 节点**（`💫SynVow_api/tools` 分类）
  - 支持 8 个产品参考图输入（严格锁定产品外观）+ 4 个风格参考图输入（提取色调/光影/排版风格）
  - 两类图片严格区分，禁止混用：产品图仅约束外观，风格图仅输出色调/背景氛围/光影/排版/构图描述
  - 支持多屏详情页叙事顺序规划（Hero → Proof → CTA），每次最多生成 20 屏提示词
  - 支持设计风格、场景偏好、输出语言等参数配置
  - 使用 SynVow 账号直接调用，无需手动填写 API Key
- **新增 `提示词文本编辑器` 节点**（`💫SynVow_api/tools` 分类）
  - 工作流执行过程中弹出交互式文本编辑界面，支持逐条编辑提示词列表
  - 点击 Continue 确认后继续执行，点击 Cancel 中断当前队列
- **优化 `GPT-Image-2 Prompt Optimizer` 节点**
  - 新增 `layout_type`（布局类型）和 `text_policy`（文字策略）参数
  - `text_policy=不加文字` 时自动清除 schema 中所有文字诱导字段
  - 新增 `visual_focus`、`layout_plan`、`typography_plan`、`copy_strategy`、`information_hierarchy` 输出字段

### 2026-05-07
- **新增 `SynVow 视频预览` 节点**（`💫SynVow_api/tools` 分类）
  - 接收 `video_path` 输入接口，支持在节点内直接预览生成的视频
  - 自动将视频复制到 ComfyUI output 目录后渲染
- **新增 `GPT-Image-2 Prompt Optimizer` 节点**（`💫SynVow_api/tools` 分类）
  - 通过 LLM 对图像生成提示词进行优化，支持多种任务类型和优化强度
- **新增取消轮询按钮**
  - 所有 SynVow 视频/图像生成节点新增 **取消轮询** 按钮，点击后发送中断信号终止当前轮询
- **视频生成节点重构**
  - `grok_synvow.py`、`veo3_synvow.py`、`sora2_synvow.py` 移除内嵌视频预览逻辑，统一交由 `SynVow 视频预览` 节点处理
- **修复** `GPT-Image-2 Prompt Optimizer` 节点在模型未返回有效内容时崩溃的问题

### 2026-04-21
- **新增 `SynVow GPT-Image-2` 节点**
  - 支持 GPT-Image-2 文生图（`gpt-image-2-文生图-默认`）和图生图（`gpt-image-2-图生图-默认`）
  - 图生图最多支持 4 张输入图（base64 编码传输）
  - 支持尺寸选择：`1024x1024`、`1536x1024`、`1024x1536`
  - 采用异步提交 + 轮询机制，携带 `consumption_id` 支持失败自动退费
  - 输出图像张量、图片 URL、响应信息及对话历史

### 2026-04-10
- **新增 `SynVow 文本分割` 节点**（`💫SynVow_api/tools` 分类）
  - 按分隔符切分文本
  - 输出 `text`（单条/全文）和 `list`（列表，可直接接批量节点 `prompts_list`）

---

## License

MIT
