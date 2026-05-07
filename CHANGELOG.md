# Changelog

## 2026/5/7

### 新增节点

#### SynVow 视频预览 (`py/tools/synvow_video_preview.py`)
- 新增 `SynVow 视频预览` 节点（`💫SynVow_api/tools` 分类）
- 接收 `video_path` 输入接口（纯连线，无输入框），支持在节点内直接预览生成的视频
- 自动将视频复制到 ComfyUI output 目录后渲染

#### GPT-Image-2 Prompt Optimizer (`py/api/gpt_image2_prompt_optimizer.py`)
- 新增 `GPT-Image-2 Prompt Optimizer` 节点（`💫SynVow_api/tools` 分类）
- 通过 LLM 对图像生成提示词进行优化，支持多种任务类型和优化强度

### 功能改进

#### 取消轮询按钮 (`web/synvow_cancel_poll.js`)
- 所有 SynVow 视频/图像生成节点新增 **取消轮询** 按钮
- 点击后向 ComfyUI 发送 `/interrupt` 中断信号，终止当前轮询
- 支持拖出新节点时自动添加按钮

#### 视频生成节点清理
- `grok_synvow.py`、`veo3_synvow.py`、`sora2_synvow.py` 移除内嵌视频预览逻辑，统一交由 `SynVow 视频预览` 节点处理
- `video_preview.js` 改为只对 `SynVowApiVideoPreview` 节点生效

#### `video_common.py`
- 补充 `extract_queue_ticket` 和 `wait_for_queue_ready` 函数，供排队任务状态轮询使用

### 修复

#### `gpt_image2_prompt_optimizer.py`
- 修复 `parse_chat_response` 返回 `None` 时触发 `AttributeError` 的问题，改为抛出明确错误信息

## 2026/4/21

### 新增节点

#### SynVow GPT-Image-2 (`gpt_image_2_synvow.py`)
- 新增 `SynVowGptImage2` 节点，支持通过 SynVow API 调用 GPT-Image-2 模型
- 支持**文生图**（`gpt-image-2-文生图-默认`）和**图生图**（`gpt-image-2-图生图-默认`）两种模式
- 根据模型名称自动区分模式，文生图无需传入图片，图生图支持最多 4 张输入图（base64 编码）
- 支持尺寸选择：`1024x1024`、`1536x1024`、`1024x1536`
- 采用异步提交 + 轮询机制：提交任务后轮询 `/api/models/tasks`，最长等待 600 秒
- 提交时携带 `consumption_id`，任务失败时后端可自动退费
- 支持对话历史记录（`clear_chats` 参数控制是否清除）
- 输出：图像张量、响应信息、图片 URL、对话历史

### 修改

#### `nanobanana_synvow.py`
- 轮询时增加完整响应日志打印，便于排查状态字段异常
