<template>
  <NodeCard v-bind="{ ...props, ...$attrs }" title="seedance2.0" :minW="300">
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="图像" data-port-type="input" data-port-data-type="image"
        @pointerdown.stop="emit('portDragStart', id, '图像', 'input', $event)"
      ></div>
      <span>图像</span>
      <span class="port-spacer"></span>
      <span>视频</span>
      <div
        class="port-dot output-dot"
        :data-node-id="id" data-port="视频" data-port-type="output" data-port-data-type="video"
        @pointerdown.stop="emit('portDragStart', id, '视频', 'output', $event)"
      ></div>
    </div>
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="视频" data-port-type="input" data-port-data-type="video"
        @pointerdown.stop="emit('portDragStart', id, '视频', 'input', $event)"
      ></div>
      <span>视频</span>
      <span class="port-spacer"></span>
    </div>
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="音频" data-port-type="input" data-port-data-type="audio"
        @pointerdown.stop="emit('portDragStart', id, '音频', 'input', $event)"
      ></div>
      <span>音频</span>
      <span class="port-spacer"></span>
    </div>
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="提示词列表" data-port-type="input" data-port-data-type="string"
        @pointerdown.stop="emit('portDragStart', id, '提示词列表', 'input', $event)"
      ></div>
      <span>提示词列表</span>
      <span class="port-spacer"></span>
    </div>

    <NodeWidget :nodeId="id" port="模型" dataType="string" widgetType="select" noPort v-model="model" :options="modelOptions" />
    <NodeWidget :nodeId="id" port="宽高比" dataType="string" widgetType="select" noPort v-model="ratio" :options="ratioOptions" />
    <NodeWidget :nodeId="id" port="视频时长" dataType="string" widgetType="select" noPort v-model="duration" :options="durationOptions" />
    <NodeWidget :nodeId="id" port="分辨率" dataType="string" widgetType="select" noPort v-model="resolution" :options="resolutionOptions" />

    <template #body>
      <div class="tl-body sd-body" @pointerdown.stop>
        <div
          ref="gridContainerRef"
          class="ni-grid-container sd-grid-12"
          :class="{ 'ni-drag-over': isDragOver && dragSrcIndex === -1 && dragOverIndex === -1 }"
          @pointerdown.stop
        >
          <div
            v-for="(item, i) in gridSlots"
            :key="i"
            class="ni-grid-cell sd-grid-cell"
            :class="{ 'ni-grid-cell-drag-over': dragOverIndex === i, 'ni-grid-cell-dragging': dragSrcIndex === i }"
            @click="() => onCellClick(i)"
            @pointerdown.stop="onCellPointerDown(i)"
          >
            <template v-if="item">
              <img v-if="item.mediaType === 'image'" :src="item.fileUrl" class="ni-grid-img" draggable="false" />
              <div v-else class="sd-media-box">
                <VideoIcon v-if="item.mediaType === 'video'" :size="20" />
                <MusicIcon v-else :size="20" />
                <span>{{ item.fileName }}</span>
              </div>
              <button class="ni-grid-remove-btn" @click.stop="removeFile(i)" @pointerdown.stop>
                <XIcon :size="12" />
              </button>
            </template>
            <template v-else>
              <div class="ni-grid-placeholder sd-grid-placeholder">
                <ImageIcon :size="18" />
                <VideoIcon :size="18" />
                <MusicIcon :size="18" />
              </div>
            </template>
          </div>
        </div>

        <div class="tl-item" @mouseenter="promptHover = true" @mouseleave="promptHover = false">
          <textarea
            class="node-input tl-textarea gm-textarea sd-textarea"
            v-model="prompt"
            :placeholder="promptListConnected ? '已接入提示词列表，此输入框无效' : '请输入提示词'"
            :disabled="promptListConnected"
            :class="{ 'nb-textarea-disabled': promptListConnected }"
            @wheel.stop.passive
          ></textarea>
          <div class="tl-actions" :class="{ visible: promptHover }">
            <button class="tl-btn" :title="promptCopied ? '已复制' : '复制'" @click="copyPrompt(prompt)" @pointerdown.stop>
              <Check v-if="promptCopied" :size="12" /><Copy v-else :size="12" />
            </button>
          </div>
        </div>
      </div>
    </template>
  </NodeCard>
</template>

<script lang="ts">
export const SeedanceNodeDef = {
  type: 'ai-video/seedance2',
  label: 'seedance2.0',
  inputs: [
    { name: '图像', type: 'image' },
    { name: '视频', type: 'video' },
    { name: '音频', type: 'audio' },
    { name: '提示词列表', type: 'string' },
  ],
  outputs: [{ name: '视频', type: 'video' }],
  defaultData: {
    model: 'seedance2.0-fast',
    ratio: 'adaptive',
    duration: '5',
    resolution: '720p',
    localFiles: Array(12).fill(null),
    prompt: '',
  },
}
</script>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Image as ImageIcon, Video as VideoIcon, Music as MusicIcon, X as XIcon, Copy, Check } from 'lucide-vue-next'
import NodeCard from '../NodeCard.vue'
import NodeWidget from '../NodeWidget.vue'
import type { NodeBaseProps, NodePortEmits } from '../types'
import { useNodeData } from '../useNodeData'
import { useCanvasStore } from '../../core/store'
import { useCopy } from '../useCopy'
import { fileNameFromPath, normalizeTauriFilePath } from '../../core/tauriFileDrop'
import { nativeDragDropEvent } from '../../core/dragDropStore'

type SeedanceMediaType = 'image' | 'video' | 'audio'
interface SeedanceMediaFile {
  filePath: string
  fileName: string
  fileUrl: string
  mediaType: SeedanceMediaType
}

const MAX_FILES = 12
const IMAGE_EXTS = ['jpg','jpeg','png','gif','webp','bmp','svg','tiff','ico']
const VIDEO_EXTS = ['mp4','mov','avi','mkv','webm','flv','wmv']
const AUDIO_EXTS = ['mp3','wav','ogg','flac','aac','m4a']

defineOptions({ inheritAttrs: false })
const props = defineProps<NodeBaseProps>()
const emit = defineEmits<NodePortEmits>()
const { id } = props

const nodeData = useNodeData(id)
const canvasStore = useCanvasStore()

const modelOptions = [
  { value: 'seedance2.0', label: 'seedance2.0' },
  { value: 'seedance2.0-fast', label: 'seedance2.0-fast' },
]
const ratioOptions = [
  { value: 'adaptive', label: '自适应' },
  { value: '16:9', label: '16:9' },
  { value: '4:3', label: '4:3' },
  { value: '1:1', label: '1:1' },
  { value: '3:4', label: '3:4' },
  { value: '9:16', label: '9:16' },
  { value: '21:9', label: '21:9' },
]
const durationOptions = ['5', '10', '15'].map(v => ({ value: v, label: `${v}s` }))
const resolutionOptions = [
  { value: '720p', label: '720P' },
  { value: '480p', label: '480P' },
]

const normalizeModel = (v: string) => v === 'seedance_2' ? 'seedance2.0' : v === 'seedance_2_fast' ? 'seedance2.0-fast' : v
const model = computed({ get: () => normalizeModel(nodeData.value?.model ?? 'seedance2.0-fast'), set: v => { if (nodeData.value) nodeData.value.model = v } })
const ratio = computed({ get: () => nodeData.value?.ratio ?? 'adaptive', set: v => { if (nodeData.value) nodeData.value.ratio = v } })
const duration = computed({ get: () => String(nodeData.value?.duration ?? '5'), set: v => { if (nodeData.value) nodeData.value.duration = v } })
const resolution = computed({ get: () => nodeData.value?.resolution ?? '720p', set: v => { if (nodeData.value) nodeData.value.resolution = v } })
const prompt = computed({ get: () => nodeData.value?.prompt ?? '', set: v => { if (nodeData.value) nodeData.value.prompt = v } })

const { hover: promptHover, copied: promptCopied, copy: copyPrompt } = useCopy()
const promptListConnected = computed(() => canvasStore.canvasLinks.some(l => l.toNode === id && l.toPort === '提示词列表'))
const localFiles = computed<(SeedanceMediaFile | null)[]>(() => Array.isArray(nodeData.value?.localFiles) ? nodeData.value.localFiles : [])
const gridSlots = computed<(SeedanceMediaFile | null)[]>(() => {
  const files = localFiles.value.slice(0, MAX_FILES)
  return [...files, ...Array(MAX_FILES - files.length).fill(null)]
})

const gridContainerRef = ref<HTMLElement | null>(null)
const dragSrcIndex = ref(-1)
const dragOverIndex = ref(-1)
const isDragOver = ref(false)
let lastDragTargetIdx = -1
let pointerDragMoved = false
let stopNativeDragWatch: (() => void) | null = null

const saveFiles = (files: (SeedanceMediaFile | null)[]) => {
  if (nodeData.value) nodeData.value.localFiles = files
}
const removeFile = (i: number) => {
  const filtered = gridSlots.value.filter((_, k) => k !== i)
  saveFiles(Array.from({ length: MAX_FILES }, (_, j) => filtered[j] ?? null))
}
const mediaTypeFromPath = (path: string): SeedanceMediaType | null => {
  const ext = path.split('?')[0].split('.').pop()?.toLowerCase() ?? ''
  if (IMAGE_EXTS.includes(ext)) return 'image'
  if (VIDEO_EXTS.includes(ext)) return 'video'
  if (AUDIO_EXTS.includes(ext)) return 'audio'
  return null
}
const mediaTypeFromFile = (file: File): SeedanceMediaType | null => {
  if (file.type.startsWith('image/')) return 'image'
  if (file.type.startsWith('video/')) return 'video'
  if (file.type.startsWith('audio/')) return 'audio'
  return mediaTypeFromPath(file.name)
}
const getCellIndexAt = (x: number, y: number, physical = false): number => {
  const container = gridContainerRef.value
  if (!container) return -1
  const dpr = physical ? (window.devicePixelRatio || 1) : 1
  const cx = x / dpr; const cy = y / dpr
  const cells = container.querySelectorAll<HTMLElement>('.ni-grid-cell')
  for (let i = 0; i < cells.length; i++) {
    const r = cells[i].getBoundingClientRect()
    if (cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom) return i
  }
  return -1
}
const resetDragState = () => { dragSrcIndex.value = -1; dragOverIndex.value = -1 }
const loadPathToSlot = async (path: string, slotIndex: number) => {
  const mediaType = mediaTypeFromPath(path)
  if (!mediaType) return
  const normalizedPath = normalizeTauriFilePath(path)
  const { convertFileSrc } = await import('@tauri-apps/api/core')
  const files = [...gridSlots.value]
  files[slotIndex] = { filePath: normalizedPath, fileName: fileNameFromPath(normalizedPath), fileUrl: convertFileSrc(normalizedPath), mediaType }
  saveFiles(files)
}
const findEmptySlots = (): number[] => gridSlots.value.map((file, i) => (!file?.fileUrl ? i : -1)).filter(i => i !== -1)
const loadPathsFromSlot = async (paths: string[], slotIndex: number) => {
  const mediaPaths = paths.filter(p => !!mediaTypeFromPath(p))
  if (!mediaPaths.length) return
  await loadPathToSlot(mediaPaths[0], slotIndex)
  const usedSlots = new Set<number>([slotIndex])
  const emptySlots = findEmptySlots()
  for (let i = 1; i < mediaPaths.length; i++) {
    const nextEmpty = emptySlots.find(s => !usedSlots.has(s))
    if (nextEmpty == null) break
    await loadPathToSlot(mediaPaths[i], nextEmpty)
    usedSlots.add(nextEmpty)
  }
}
const onCellPointerDown = (idx: number) => {
  if (!gridSlots.value[idx]?.fileUrl) return
  dragSrcIndex.value = idx; dragOverIndex.value = idx
  pointerDragMoved = false
  window.addEventListener('pointermove', onCellPointerMove)
  window.addEventListener('pointerup', onCellPointerUp, { once: true })
}
const onCellPointerMove = (e: PointerEvent) => {
  if (dragSrcIndex.value === -1) return
  pointerDragMoved = true
  dragOverIndex.value = getCellIndexAt(e.clientX, e.clientY)
}
const onCellPointerUp = (e: PointerEvent) => {
  window.removeEventListener('pointermove', onCellPointerMove)
  const src = dragSrcIndex.value
  const targetIdx = getCellIndexAt(e.clientX, e.clientY)
  if (src !== -1 && targetIdx !== -1 && src !== targetIdx) {
    const files = [...gridSlots.value]
    ;[files[src], files[targetIdx]] = [files[targetIdx], files[src]]
    saveFiles(files)
  }
  resetDragState()
}
const onCellClick = (i: number) => {
  if (pointerDragMoved) { pointerDragMoved = false; return }
  if (gridSlots.value[i]) return
  const input = document.createElement('input')
  input.type = 'file'; input.accept = 'image/*,video/*,audio/*'; input.multiple = true
  input.onchange = () => {
    const selected = Array.from(input.files ?? []).map(file => ({ file, mediaType: mediaTypeFromFile(file) })).filter(x => x.mediaType)
    const files = [...gridSlots.value]
    let slot = i
    for (const item of selected) {
      while (slot < MAX_FILES && files[slot]) slot++
      if (slot >= MAX_FILES) break
      files[slot] = { filePath: '', fileName: item.file.name, fileUrl: URL.createObjectURL(item.file), mediaType: item.mediaType! }
      slot++
    }
    saveFiles(files)
  }
  input.click()
}
const setupTauriFileDrop = () => {
  stopNativeDragWatch = watch(nativeDragDropEvent, async payload => {
    if (!payload) return
    const pos = payload.position
    if (payload.type === 'enter' || payload.type === 'over') {
      if (pos) {
        const idx = getCellIndexAt(pos.x, pos.y, true)
        dragOverIndex.value = idx
        isDragOver.value = idx === -1
        if (idx !== -1) lastDragTargetIdx = idx
      }
      return
    }
    if (payload.type === 'drop') {
      const mediaPaths = (payload.paths ?? []).map(normalizeTauriFilePath).filter(p => !!mediaTypeFromPath(p))
      const targetIdx = pos ? getCellIndexAt(pos.x, pos.y, true) : lastDragTargetIdx
      if (targetIdx !== -1 && mediaPaths.length) await loadPathsFromSlot(mediaPaths, targetIdx)
      lastDragTargetIdx = -1; isDragOver.value = false; resetDragState()
      return
    }
    if (payload.type === 'leave' || payload.type === 'cancelled') {
      lastDragTargetIdx = -1; isDragOver.value = false; resetDragState()
    }
  })
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onCellPointerMove)
  if (stopNativeDragWatch) { stopNativeDragWatch(); stopNativeDragWatch = null }
})
onMounted(async () => {
  setupTauriFileDrop()
  const saved = nodeData.value?.localFiles ?? []
  if (!saved.length) return
  const { convertFileSrc } = await import('@tauri-apps/api/core')
  const { exists } = await import('@tauri-apps/plugin-fs')
  for (let i = 0; i < saved.length; i++) {
    const item = saved[i]
    if (!item) continue
    if (item.filePath) {
      if (await exists(item.filePath)) {
        if (nodeData.value?.localFiles?.[i]) nodeData.value.localFiles[i].fileUrl = convertFileSrc(item.filePath)
      } else if (nodeData.value?.localFiles?.[i]) {
        nodeData.value.localFiles[i] = null
      }
    } else if (item.fileUrl?.startsWith('blob:')) {
      if (nodeData.value?.localFiles?.[i]) nodeData.value.localFiles[i] = null
    }
  }
})
</script>

<style>
@import '../../styles/node-ai-gen.css';
@import '../../styles/node-image.css';
</style>
