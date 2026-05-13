import { useAuthStore } from '../../../core/authStore'
import { useCanvasStore, TaskStoppedError } from '../../../core/canvasStore'
import type { StoreCanvasNode } from '../../../core/store'

const SYNVOW_BASE = 'https://service.synvow.com/api/v1'
const SUBMIT_URL = `${SYNVOW_BASE}/api/models/image/edit`
const POLL_URL = `${SYNVOW_BASE}/api/models/tasks`

type MediaType = 'image' | 'video' | 'audio'
type CoolFile = { url: string; type: MediaType; name?: string }
type LocalMedia = { filePath?: string; fileName?: string; fileUrl?: string; mediaType?: MediaType }

const IMAGE_EXTS = ['jpg','jpeg','png','gif','webp','bmp']
const VIDEO_EXTS = ['mp4','mov','avi','mkv','webm','flv','wmv']
const AUDIO_EXTS = ['mp3','wav','ogg','flac','aac','m4a']

function normalizeModel(model: string): string {
  if (model === 'seedance_2') return 'seedance2.0'
  if (model === 'seedance_2_fast') return 'seedance2.0-fast'
  return model
}

function mediaTypeFromUrl(url: string): MediaType | null {
  const ext = url.split('?')[0].split('.').pop()?.toLowerCase() ?? ''
  if (IMAGE_EXTS.includes(ext)) return 'image'
  if (VIDEO_EXTS.includes(ext)) return 'video'
  if (AUDIO_EXTS.includes(ext)) return 'audio'
  return null
}

function mimeFromPath(path: string, mediaType: MediaType): string {
  const ext = path.split('?')[0].split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = {
    jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', gif: 'image/gif', bmp: 'image/bmp',
    mp4: 'video/mp4', mov: 'video/quicktime', avi: 'video/x-msvideo', mkv: 'video/x-matroska', webm: 'video/webm', flv: 'video/x-flv', wmv: 'video/x-ms-wmv',
  }
  return map[ext] ?? `${mediaType}/*`
}

async function uploadWithApiKey(apiKey: string, filePath: string, mediaType: MediaType): Promise<string> {
  if (mediaType === 'audio') throw new Error('Seedance2.0 暂不支持本地音频上传，请使用公网音频 URL 输入')
  const { readFile } = await import('@tauri-apps/plugin-fs')
  const bytes = await readFile(filePath)
  const mime = mimeFromPath(filePath, mediaType)
  const fileName = filePath.split(/[\\/]/).pop() || 'file'
  const form = new FormData()
  form.append('files', new Blob([bytes], { type: mime }), fileName)
  const uploadUrl = `${SYNVOW_BASE}${mediaType === 'image' ? '/api/upload/images' : '/api/upload/videos'}`
  console.log('[Seedance2.0] API Key 上传请求:', { uploadUrl, mediaType, filePath, fileName, mime, size: bytes.length })
  const res = await fetch(uploadUrl, { method: 'POST', headers: { 'X-API-Key': apiKey }, body: form })
  const data = await res.json() as any
  console.log('[Seedance2.0] API Key 上传响应:', { status: res.status, data })
  if (!res.ok || data?.code !== 200) throw new Error(data?.message ?? `${mediaType} 上传失败`)
  const url = data?.data?.urls?.[0]
  if (!url) throw new Error(`${mediaType} 上传响应中无 URL`)
  return url
}

async function toCoolFile(apiKey: string, item: LocalMedia | string, fallbackType?: MediaType): Promise<CoolFile | null> {
  if (typeof item === 'string') {
    const type = fallbackType ?? mediaTypeFromUrl(item)
    if (!type) return null
    console.log('[Seedance2.0] 使用输入 URL:', { type, url: item })
    return { url: item, type }
  }
  const type = item.mediaType ?? (item.filePath ? mediaTypeFromUrl(item.filePath) : item.fileUrl ? mediaTypeFromUrl(item.fileUrl) : null)
  if (!type) return null
  const rawUrl = String(item.fileUrl ?? '')
  if (/^https?:\/\/asset\.localhost/i.test(rawUrl)) {
    if (!item.filePath) throw new Error('Seedance2.0 媒体 URL 不是公网地址，且缺少本地路径，无法上传')
    const url = await uploadWithApiKey(apiKey, item.filePath, type)
    console.log('[Seedance2.0] asset.localhost 已上传为公网 URL:', { type, rawUrl, url, name: item.fileName })
    return { url, type, name: item.fileName }
  }
  if (/^https?:\/\//i.test(rawUrl)) {
    console.log('[Seedance2.0] 使用媒体公网 URL:', { type, url: rawUrl, name: item.fileName })
    return { url: rawUrl, type, name: item.fileName }
  }
  if (!item.filePath) throw new Error('Seedance2.0 媒体未获取到公网 URL，已停止生成')
  const url = await uploadWithApiKey(apiKey, item.filePath, type)
  console.log('[Seedance2.0] 本地媒体已上传为公网 URL:', { type, url, name: item.fileName })
  return { url, type, name: item.fileName }
}

async function prepareInputFiles(apiKey: string, nd: any, inputs: Record<string, any>): Promise<CoolFile[]> {
  console.log('[Seedance2.0] 开始准备媒体文件：先上传图像/视频，获取 URL 后再生成')
  const files: CoolFile[] = []
  for (const [port, type] of [['图像', 'image'], ['视频', 'video'], ['音频', 'audio']] as const) {
    const raw = inputs[port]
    const list = raw == null ? [] : Array.isArray(raw) ? raw : [raw]
    console.log('[Seedance2.0] 端口媒体输入:', { port, type, count: list.length })
    for (const item of list) {
      const file = await toCoolFile(apiKey, item, type)
      if (file) files.push(file)
    }
  }
  if (!files.length) {
    const localItems = (nd.localFiles ?? []).filter(Boolean)
    console.log('[Seedance2.0] 端口无媒体，使用本地宫格媒体:', { count: localItems.length })
    for (const item of localItems) {
      const file = await toCoolFile(apiKey, item)
      if (file) files.push(file)
    }
  }
  console.log('[Seedance2.0] 媒体 URL 准备完成:', files)
  return files
}

function assignMediaFields(body: Record<string, any>, files: CoolFile[]) {
  if (files.length) body.files = files.map(f => ({ url: f.url, type: f.type }))
}

function extractTaskId(data: any): string {
  return data?.task_id ?? data?.data?.task_id ?? data?.data?.data?.task_id ?? data?.sourceData?.task_id ?? data?.data?.sourceData?.task_id ?? ''
}

function extractConsumptionId(data: any): string {
  return data?.consumption_id ?? data?.data?.consumption_id ?? ''
}

async function submitTask(apiKey: string, body: Record<string, any>): Promise<{ taskId: string; consumptionId: string }> {
  console.log('[Seedance2.0] 提交生成请求:', JSON.stringify(body).slice(0, 1000))
  const res = await fetch(SUBMIT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
    body: JSON.stringify(body),
  })
  const data = await res.json() as any
  console.log('[Seedance2.0] 提交生成响应:', { status: res.status, data })
  if (!res.ok) throw new Error(data?.message ?? `Seedance2.0 提交失败: HTTP ${res.status}`)
  const taskId = extractTaskId(data)
  if (!taskId) throw new Error(`Seedance2.0 响应中无 task_id: ${JSON.stringify(data).slice(0, 200)}`)
  return { taskId, consumptionId: extractConsumptionId(data) }
}

function extractVideoUrl(data: any): string {
  if (!data) return ''
  if (typeof data === 'string' && /^https?:\/\//i.test(data)) return data
  if (Array.isArray(data)) return data.map(extractVideoUrl).find(Boolean) ?? ''
  if (typeof data === 'object') {
    if (typeof data.url === 'string') return data.url
    if (typeof data.video_url === 'string') return data.video_url
    if (typeof data.video === 'string') return data.video
    for (const key of ['data', 'result', 'output', 'sourceData', 'task_result', 'videos']) {
      const found = extractVideoUrl(data[key])
      if (found) return found
    }
  }
  return ''
}

async function pollTask(apiKey: string, taskId: string, model: string, consumptionId: string, isStopped: () => boolean): Promise<string> {
  const timeout = 1_800_000
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
      if (!res.ok) { console.warn('[Seedance2.0] 轮询 HTTP 错误:', res.status, await res.text().catch(() => '')); continue }
      const json = await res.json()
      const data = (json?.data ?? json) as any
      const status = String(data?.status ?? data?.task_status ?? '')
      console.log('[Seedance2.0] 轮询结果 status:', status, '| raw:', JSON.stringify(json).slice(0, 300))
      if (['SUCCESS', 'success', 'succeed', 'completed', 'done', 'finished'].includes(status)) {
        const url = extractVideoUrl(data?.data ?? data)
        if (!url) throw new Error('Seedance2.0 任务成功但无视频 URL')
        return url
      }
      if (['FAILURE', 'failed', 'error'].includes(status)) {
        throw new Error(`Seedance2.0 任务失败: ${data?.fail_reason ?? data?.error ?? status}`)
      }
    } catch (e: any) {
      if (e.message?.startsWith('Seedance2.0')) throw e
    }
  }
  throw new Error('Seedance2.0 轮询超时')
}

export async function executeSeedance(node: StoreCanvasNode, inputs: Record<string, any>, storeTaskId?: string): Promise<Record<string, any>> {
  const nd = node as any
  const authStore = useAuthStore()
  const canvasStore = useCanvasStore()
  const isStopped = () => !!storeTaskId && canvasStore.isTaskStopped(storeTaskId)
  if (!authStore.isLoggedIn) throw new Error('请先登录后再运行 Seedance2.0 节点')
  if (!authStore.apiKey) await authStore.fetchAndSaveApiKey()
  if (!authStore.apiKey) throw new Error('获取 API Key 失败，请重新登录后再运行')

  const inputFiles = await prepareInputFiles(authStore.apiKey, nd, inputs)

  const promptListInput = inputs['提示词列表']
  const prompts = promptListInput != null
    ? (Array.isArray(promptListInput) ? promptListInput : [promptListInput]).map(String).filter(s => s.trim())
    : [String(nd.prompt ?? '').trim()].filter(s => s)
  if (!prompts.length) throw new Error('Seedance2.0 请输入提示词或连接提示词列表')

  const model = normalizeModel(nd.model ?? 'seedance2.0-fast')
  const submitted: { taskId: string; consumptionId: string }[] = []
  for (const prompt of prompts) {
    const body: Record<string, any> = {
      prompt,
      model,
      ratio: nd.ratio ?? 'adaptive',
      duration: parseInt(String(nd.duration ?? '5')) || 5,
      resolution: nd.resolution ?? '720p',
    }
    assignMediaFields(body, inputFiles)
    console.log('[Seedance2.0] 已获取媒体 URL，开始生成:', { prompt, mediaCount: inputFiles.length, body })
    submitted.push(await submitTask(authStore.apiKey, body))
    await new Promise(r => setTimeout(r, 1000))
  }

  const results = await Promise.allSettled(submitted.map(s => pollTask(authStore.apiKey, s.taskId, model, s.consumptionId, isStopped)))
  if (results.some(r => r.status === 'rejected' && r.reason instanceof TaskStoppedError)) throw new TaskStoppedError()
  const failures = results.filter(r => r.status === 'rejected') as PromiseRejectedResult[]
  if (failures.length) throw new Error(failures.map(f => f.reason?.message ?? String(f.reason)).join('; '))
  const urls = (results as PromiseFulfilledResult<string>[]).map(r => r.value).filter(Boolean)
  return { '视频': urls.length === 1 ? urls[0] : urls }
}
