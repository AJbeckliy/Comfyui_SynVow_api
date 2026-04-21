# Changelog

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
