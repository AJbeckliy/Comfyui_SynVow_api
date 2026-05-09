// GPT-image 节点执行器
import { useAuthStore } from '../../../core/authStore'
import { useCanvasStore, TaskStoppedError } from '../../../core/canvasStore'
import type { StoreCanvasNode } from '../../../core/store'

const API_BASE  = 'https://service.synvow.com/api/v1'
const SUBMIT_URL = `${API_BASE}/api/models/image/edit`
const POLL_URL   = `${API_BASE}/api/models/tasks`

// 图像 URL → base64 data URI
async function urlToBase64(url: string): Promise<string> {
  const res = await fetch(url)
  const blob = await res.blob()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

// 从响应中递归提取图片 URL
function extractUrls(d: any): string[] {
  if (Array.isArray(d)) return d.flatMap((item: any) => item?.url ? [item.url] : [])
  if (d && typeof d === 'object') {
    if (d.url) return [d.url]
    for (const key of ['data', 'sourceData', 'images']) {
      if (d[key]) { const r = extractUrls(d[key]); if (r.length) return r }
    }
  }
  return []
}

// 轮询单个任务，返回图像 URL 数组
async function pollTask(taskId: string, model: string, consumptionId: string, apiKey: string, _storeTaskId: string, isStopped: () => boolean): Promise<string[]> {
  const timeout = 900_000
  const interval = 5000
  const start = Date.now()
  const headers = { 'X-API-Key': apiKey, 'Content-Type': 'application/json' }
  const body: Record<string, string> = { task_id: taskId, model }
  if (consumptionId) body.consumption_id = consumptionId

  while (Date.now() - start < timeout) {
    if (isStopped()) throw new TaskStoppedError()
    await new Promise(r => setTimeout(r, interval))
    if (isStopped()) throw new TaskStoppedError()
    try {
      const res = await fetch(POLL_URL, { method: 'POST', headers, body: JSON.stringify(body) })
      if (!res.ok) { console.warn('[GPT-image] 轮询 HTTP 错误:', res.status); continue }
      const json = await res.json()
      const data = (json?.data ?? json) as any
      const status: string = data?.status ?? ''
      console.log('[GPT-image] 轮询结果 status:', status, '| raw:', JSON.stringify(json).slice(0, 300))
      if (['SUCCESS', 'success', 'completed', 'done', 'finished'].includes(status)) {
        const urls = extractUrls(data?.data ?? data)
        console.log('[GPT-image] 提取到图片 URL:', urls)
        return urls
      }
      if (['FAILURE', 'failed', 'error'].includes(status)) {
        throw new Error(`GPT-image 任务失败: ${data?.fail_reason ?? status}`)
      }
    } catch (e: any) {
      if (e.message?.startsWith('GPT-image')) throw e
    }
  }
  throw new Error('GPT-image 轮询超时（600s）')
}

// 提交单次任务，返回 { taskId, consumptionId }
async function submitTask(
  apiKey: string,
  model: string,
  prompt: string,
  size: string,
  quality: string,
  base64Images: string[],
): Promise<{ taskId: string; consumptionId: string }> {
  const headers = { 'X-API-Key': apiKey, 'Content-Type': 'application/json' }
  const payload: Record<string, any> = { model, prompt }
  if (size && size !== 'auto') payload.size = size
  if (quality && quality !== 'auto') payload.quality = quality
  if (base64Images.length > 0) {
    payload.image = base64Images[0]
    if (base64Images.length > 1) payload.images = base64Images.slice(1)
  }

  console.log('[GPT-image] 提交请求 payload:', JSON.stringify(payload).slice(0, 500))
  const res = await fetch(`${SUBMIT_URL}?async=true`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
  const json = await res.json()
  console.log('[GPT-image] 提交响应 status:', res.status, '| body:', JSON.stringify(json).slice(0, 500))
  if (!res.ok) {
    const msg = json?.message ?? JSON.stringify(json).slice(0, 200)
    const err = new Error(`GPT-image 提交失败: HTTP ${res.status} ${msg}`)
    ;(err as any).status = res.status
    throw err
  }

  const d = json as any
  const taskId: string =
    d?.task_id ?? d?.data?.task_id ?? (d?.data?.sourceData?.task_id) ?? ''
  if (!taskId) throw new Error(`GPT-image 响应中无 task_id: ${JSON.stringify(json).slice(0, 200)}`)
  const consumptionId: string = d?.consumption_id ?? d?.data?.consumption_id ?? ''
  return { taskId, consumptionId }
}

export async function executeGptImage(
  node: StoreCanvasNode,
  inputs: Record<string, any>,
  storeTaskId?: string,
): Promise<Record<string, any>> {
  const nd = node as any
  const authStore = useAuthStore()
  const canvasStore = useCanvasStore()
  const isStopped = () => !!storeTaskId && canvasStore.isTaskStopped(storeTaskId)
  if (!authStore.apiKey) throw new Error('请先登录后再运行 GPT-image 节点')

  const modelType: string = nd.modelType ?? 'gpt-image-2-text'
  const mode: string      = nd.mode     ?? '默认'
  const size: string      = nd.size     ?? 'auto'
  const quality: string   = nd.quality  ?? 'auto'
  const isTextToImage     = modelType === 'gpt-image-2-text'
  const modelLabel        = isTextToImage ? '文生图' : '图生图'
  const model             = `gpt-image-2-${modelLabel}-${mode}`

  // ── 图像准备（仅图生图用，文生图忽略） ────────────────────────────
  let base64Images: string[] = []
  if (!isTextToImage) {
    const portImg = inputs['图像']
    const portImgs: string[] = portImg
      ? (Array.isArray(portImg) ? portImg : [portImg]).filter(Boolean)
      : []
    const localImgUrls: string[] = (nd.localImages ?? [])
      .filter((img: any) => img?.imageUrl)
      .map((img: any) => img.imageUrl as string)
    const rawUrls = (portImgs.length > 0 ? portImgs : localImgUrls).slice(0, 9)
    if (!rawUrls.length) throw new Error('图生图模式需要提供输入图像')
    base64Images = await Promise.all(rawUrls.map(urlToBase64))
  }

  // ── 提示词列表 ────────────────────────────────────────────────────
  const promptListInput = inputs['提示词列表']
  let prompts: string[]
  if (promptListInput != null) {
    const raw = Array.isArray(promptListInput) ? promptListInput : [promptListInput]
    prompts = raw.map(String).filter(s => s.trim())
  } else {
    const localPrompt = String(nd.prompt ?? '').trim()
    prompts = localPrompt ? [localPrompt] : ['']
  }

  // ── 串行提交 → 并发轮询 ────────────────────────────────────
  const submitted: { taskId: string; consumptionId: string }[] = []
  for (let i = 0; i < prompts.length; i++) {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        submitted.push(await submitTask(authStore.apiKey, model, prompts[i], size, quality, base64Images))
        break
      } catch (e: any) {
        if (e?.status >= 400 && e?.status < 500) throw e
        if (attempt === 2) throw e
        await new Promise(r => setTimeout(r, 2000))
      }
    }
    if (i < prompts.length - 1) await new Promise(r => setTimeout(r, 1000))
  }

  // 并发轮询
  const pollResults = await Promise.allSettled(
    submitted.map(s => pollTask(s.taskId, model, s.consumptionId, authStore.apiKey, storeTaskId ?? '', isStopped))
  )
  if (pollResults.some(r => r.status === 'rejected' && r.reason instanceof TaskStoppedError)) throw new TaskStoppedError()
  const failures = pollResults.filter(r => r.status === 'rejected') as PromiseRejectedResult[]
  if (failures.length > 0) throw new Error(failures.map(f => f.reason?.message ?? String(f.reason)).join('; '))
  const imageUrls = (pollResults as PromiseFulfilledResult<string[]>[]).flatMap(r => r.value.filter(Boolean))
  return { '图像': imageUrls.length === 1 ? imageUrls[0] : imageUrls }
}
