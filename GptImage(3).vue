<!-- GPT-image 节点：图像生成 / 图生图，9宫格 + 提示词列表批量并发 -->
<template>
  <NodeCard v-bind="{ ...props, ...$attrs }" title="GPT-image" :minW="300">
    <!-- 端口行：图像（可选输入）/ 图像（输出） -->
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="图像" data-port-type="input" data-port-data-type="image"
        @pointerdown.stop="emit('portDragStart', id, '图像', 'input', $event)"
        title="图像输入（可选，传入则走图生图）"
      ></div>
      <span>图像</span>
      <span class="port-spacer"></span>
      <span>图像</span>
      <div
        class="port-dot output-dot"
        :data-node-id="id" data-port="图像" data-port-type="output" data-port-data-type="image"
        @pointerdown.stop="emit('portDragStart', id, '图像', 'output', $event)"
      ></div>
    </div>
    <!-- 端口行：提示词列表（可选输入） -->
    <div class="port-row port-row-both">
      <div
        class="port-dot input-dot port-optional"
        :data-node-id="id" data-port="提示词列表" data-port-type="input" data-port-data-type="string"
        @pointerdown.stop="emit('portDragStart', id, '提示词列表', 'input', $event)"
        title="提示词列表（可选，多条则并发生成）"
      ></div>
      <span>提示词列表</span>
      <span class="port-spacer"></span>
    </div>

    <!-- 参数行：模型类型 -->
    <NodeWidget
      :nodeId="id" port="模型" dataType="string" widgetType="select"
      noPort
      v-model="modelType"
      :options="modelTypeOptions"
    />

    <!-- 参数行：模式 -->
    <NodeWidget
      :nodeId="id" port="模式" dataType="string" widgetType="select"
      noPort
      v-model="mode"
      :options="modeOptions"
    />
    <!-- 参数行：尺寸 -->
    <NodeWidget
      :nodeId="id" port="尺寸" dataType="string" widgetType="select"
      noPort
      v-model="size"
      :options="sizeOptions"
    />
    <!-- 参数行：画质档位 -->
    <NodeWidget
      :nodeId="id" port="画质" dataType="string" widgetType="select"
      noPort
      v-model="resolution"
      :options="resolutionOptions"
    />
    <!-- 参数行：质量 -->
    <NodeWidget
      :nodeId="id" port="质量" dataType="string" widgetType="select"
      noPort
      v-model="quality"
      :options="qualityOptions"
    />

    <template #body>
      <div class="tl-body" @pointerdown.stop>
        <!-- 3×3 图像宫格 -->
        <div
          ref="_gridContainerRef"
          class="ni-grid-container gm-grid-9"
          :class="{ 'ni-drag-over': isDragOver && dragSrcIndex === -1 && dragOverIndex === -1 }"
          @dragover.prevent="onContainerDragOver"
          @dragleave.prevent="onContainerDragLeave"
          @drop.prevent="onDropGlobal"
          @pointerdown.stop
        >
          <div
            v-for="(img, i) in gridSlots"
            :key="i"
            class="ni-grid-cell"
            :class="{ 'ni-grid-cell-drag-over': dragOverIndex === i, 'ni-grid-cell-dragging': dragSrcIndex === i }"
            :draggable="!!img?.imageUrl"
            @click="() => onCellClick(i)"
            @dragstart="(e) => onCellDragStart(e, i)"
            @dragover.prevent="(e) => onCellDragOver(e, i)"
            @dragleave="onCellDragLeave"
            @drop.prevent="(e) => onCellDrop(e, i)"
            @dragend="onCellDragEnd"
          >
            <template v-if="img">
              <img :src="img.imageUrl" class="ni-grid-img" draggable="false" />
              <button class="ni-grid-remove-btn" @click.stop="removeImage(i)" @pointerdown.stop>
                <XIcon :size="12" />
              </button>
            </template>
            <template v-else>
              <div class="ni-grid-placeholder">
                <ImageIcon :size="20" />
              </div>
            </template>
          </div>
        </div>

        <!-- 提示词输入（提示词列表接入时禁用） -->
        <div class="tl-item"
          @mouseenter="promptHover = true" @mouseleave="promptHover = false"
        >
          <textarea
            class="node-input tl-textarea gm-textarea"
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
export const GptImageNodeDef = {
  type: 'ai-image/gpt-image',
  label: 'GPT-image',
  inputs:  [
    { name: '图像', type: 'image' },
    { name: '提示词列表', type: 'string' },
  ],
  outputs: [{ name: '图像', type: 'image' }],
  defaultData: {
    modelType: 'gpt-image-2-text',
    mode: '默认',
    resolution: '1K',
    size: 'auto',
    quality: 'auto',
    localImages: Array(9).fill(null),
    prompt: '',
  },
}
</script>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Image as ImageIcon, X as XIcon, Copy, Check } from 'lucide-vue-next'
import NodeCard from '../NodeCard.vue'
import NodeWidget from '../NodeWidget.vue'
import type { NodeBaseProps, NodePortEmits } from '../types'
import { useNodeData } from '../useNodeData'
import { useCanvasStore } from '../../core/store'
import { useCopy } from '../useCopy'

interface ImageData {
  imagePath: string
  fileName: string
  imageUrl: string
}

const MAX_IMAGES = 9

defineOptions({ inheritAttrs: false })
const props = defineProps<NodeBaseProps>()
const emit = defineEmits<NodePortEmits>()
const { id } = props

const nodeData = useNodeData(id)
const canvasStore = useCanvasStore()

const modelTypeOptions = [
  { value: 'gpt-image-2-text',  label: 'gpt-image-2-文生图' },
  { value: 'gpt-image-2-image', label: 'gpt-image-2-图生图' },
]
const modeOptions = [
  { value: '默认', label: '默认' },
  { value: '优质', label: '优质' },
]

const qualityOptions = ['auto', 'low', 'medium', 'high'].map(v => ({ value: v, label: v }))
const resolutionOptions = ['1K', '2K', '4K'].map(v => ({ value: v, label: v }))

const SIZE_OPTIONS_1K = [
  { value: 'auto',      label: 'auto' },
  { value: '1024x1024', label: '1:1' },
  { value: '1536x1024', label: '16:9' },
  { value: '1024x1536', label: '9:16' },
  { value: '1360x1024', label: '4:3' },
  { value: '1024x1360', label: '3:4' },
  { value: '1280x1024', label: '5:4' },
  { value: '1024x1280', label: '4:5' },
  { value: '1152x768',  label: '3:2' },
  { value: '768x1152',  label: '2:3' },
  { value: '1536x512',  label: '3:1' },
  { value: '512x1536',  label: '1:3' },
  { value: '1280x640',  label: '2:1' },
  { value: '640x1280',  label: '1:2' },
  { value: '1792x768',  label: '21:9' },
  { value: '768x1792',  label: '9:21' },
]
const SIZE_OPTIONS_2K = [
  { value: 'auto',      label: 'auto' },
  { value: '2048x2048', label: '1:1' },
  { value: '2048x1152', label: '16:9' },
  { value: '1152x2048', label: '9:16' },
  { value: '2048x1536', label: '4:3' },
  { value: '1536x2048', label: '3:4' },
  { value: '2048x1632', label: '5:4' },
  { value: '1632x2048', label: '4:5' },
  { value: '2048x1360', label: '3:2' },
  { value: '1360x2048', label: '2:3' },
  { value: '2048x688',  label: '3:1' },
  { value: '688x2048',  label: '1:3' },
  { value: '2048x1024', label: '2:1' },
  { value: '1024x2048', label: '1:2' },
  { value: '2560x1104', label: '21:9' },
  { value: '1104x2560', label: '9:21' },
]
const SIZE_OPTIONS_4K = [
  { value: 'auto',      label: 'auto' },
  { value: '2880x2880', label: '1:1' },
  { value: '3840x2160', label: '16:9' },
  { value: '2160x3840', label: '9:16' },
  { value: '3312x2480', label: '4:3' },
  { value: '2480x3312', label: '3:4' },
  { value: '3200x2560', label: '5:4' },
  { value: '2560x3200', label: '4:5' },
  { value: '3520x2352', label: '3:2' },
  { value: '2352x3520', label: '2:3' },
  { value: '3840x1280', label: '3:1' },
  { value: '1280x3840', label: '1:3' },
  { value: '3840x1920', label: '2:1' },
  { value: '1920x3840', label: '1:2' },
  { value: '3840x1648', label: '21:9' },
  { value: '1648x3840', label: '9:21' },
]


// 切换画质档位时按比例 label 匹配，保留同比例的 value，找不到才回退 auto
function mapSizeToOptions(currentSize: string, targetOptions: typeof SIZE_OPTIONS_1K) {
  const currentLabel = [...SIZE_OPTIONS_1K, ...SIZE_OPTIONS_2K, ...SIZE_OPTIONS_4K].find(o => o.value === currentSize)?.label
  return targetOptions.find(o => o.label === currentLabel)?.value ?? 'auto'
}

const VALID_MODEL_TYPES = modelTypeOptions.map(o => o.value)
const modelType = computed({
  get: () => {
    const v = nodeData.value?.modelType
    return VALID_MODEL_TYPES.includes(v) ? v : 'gpt-image-2-text'
  },
  set: (v) => { if (nodeData.value) nodeData.value.modelType = v },
})
const mode = computed({
  get: () => nodeData.value?.mode ?? '默认',
  set: (v) => { if (nodeData.value) nodeData.value.mode = v },
})
const resolution = computed({
  get: () => nodeData.value?.resolution ?? '1K',
  set: (v) => {
    if (!nodeData.value) return
    nodeData.value.resolution = v
    const targetOpts = v === '4K' ? SIZE_OPTIONS_4K : v === '2K' ? SIZE_OPTIONS_2K : SIZE_OPTIONS_1K
    nodeData.value.size = mapSizeToOptions(nodeData.value.size ?? 'auto', targetOpts)
  },
})
const sizeOptions = computed(() => {
  if (resolution.value === '4K') return SIZE_OPTIONS_4K
  if (resolution.value === '2K') return SIZE_OPTIONS_2K
  return SIZE_OPTIONS_1K
})
const size = computed({
  get: () => nodeData.value?.size ?? 'auto',
  set: (v) => { if (nodeData.value) nodeData.value.size = v },
})
const quality = computed({
  get: () => nodeData.value?.quality ?? 'auto',
  set: (v) => { if (nodeData.value) nodeData.value.quality = v },
})
const prompt = computed({
  get: () => nodeData.value?.prompt ?? '',
  set: (v) => { if (nodeData.value) nodeData.value.prompt = v },
})

const { hover: promptHover, copied: promptCopied, copy: copyPrompt } = useCopy()

const promptListConnected = computed(() =>
  canvasStore.canvasLinks.some(l => l.toNode === id && l.toPort === '提示词列表')
)

const localImages = computed<(ImageData | null)[]>(() => {
  const raw = nodeData.value?.localImages
  return Array.isArray(raw) ? raw : []
})

const gridSlots = computed<(ImageData | null)[]>(() => {
  const imgs = localImages.value.slice(0, MAX_IMAGES)
  return [...imgs, ...Array(MAX_IMAGES - imgs.length).fill(null)]
})

const saveImages = (imgs: (ImageData | null)[]) => {
  if (nodeData.value) nodeData.value.localImages = imgs
}

const removeImage = (i: number) => {
  const filtered = gridSlots.value.filter((_, k) => k !== i)
  saveImages(Array.from({ length: MAX_IMAGES }, (_, j) => filtered[j] ?? null))
}

const dragSrcIndex = ref(-1)
const dragOverIndex = ref(-1)
const isDragOver = ref(false)

const toImageData = (file: File): ImageData => ({
  imagePath: '',
  fileName: file.name,
  imageUrl: URL.createObjectURL(file),
})

const onCellClick = (i: number) => {
  if (gridSlots.value[i]) return
  const input = document.createElement('input')
  input.type = 'file'; input.accept = 'image/*'; input.multiple = true
  input.onchange = () => {
    const files = Array.from(input.files ?? [])
    const imgs = [...gridSlots.value]
    let slot = i
    for (const f of files) {
      while (slot < MAX_IMAGES && imgs[slot]) slot++
      if (slot >= MAX_IMAGES) break
      imgs[slot] = toImageData(f)
      slot++
    }
    saveImages(imgs)
  }
  input.click()
}

const onCellDragStart = (_e: DragEvent, i: number) => {
  if (!gridSlots.value[i]) return
  dragSrcIndex.value = i
  _e.dataTransfer?.setData('text/plain', String(i))
}

const onCellDragOver = (_e: DragEvent, i: number) => { dragOverIndex.value = i }
const onCellDragLeave = () => { dragOverIndex.value = -1 }

const onCellDrop = (_e: DragEvent, targetIdx: number) => {
  const srcIdx = dragSrcIndex.value
  if (srcIdx === -1 || srcIdx === targetIdx) {
    dragSrcIndex.value = -1; dragOverIndex.value = -1; return
  }
  const imgs = [...gridSlots.value]
  ;[imgs[srcIdx], imgs[targetIdx]] = [imgs[targetIdx], imgs[srcIdx]]
  saveImages(imgs)
  dragSrcIndex.value = -1; dragOverIndex.value = -1
}

const onCellDragEnd = () => { dragSrcIndex.value = -1; dragOverIndex.value = -1 }
const onContainerDragOver = () => { isDragOver.value = true }
const onContainerDragLeave = () => { isDragOver.value = false }

const onDropGlobal = (e: DragEvent) => {
  isDragOver.value = false
  if (dragSrcIndex.value !== -1) return
  const files = Array.from(e.dataTransfer?.files ?? []).filter(f => f.type.startsWith('image/'))
  if (!files.length) return
  const imgs = [...gridSlots.value]
  let slot = 0
  for (const f of files) {
    while (slot < MAX_IMAGES && imgs[slot]) slot++
    if (slot >= MAX_IMAGES) break
    imgs[slot] = toImageData(f)
  }
  saveImages(imgs)
}

onMounted(async () => {
  const saved = nodeData.value?.localImages ?? []
  if (!saved.length) return
  const { convertFileSrc } = await import('@tauri-apps/api/tauri')
  const { exists } = await import('@tauri-apps/api/fs')
  for (let i = 0; i < saved.length; i++) {
    const img = saved[i]
    if (!img) continue
    if (img.imagePath) {
      if (await exists(img.imagePath)) {
        if (nodeData.value?.localImages?.[i]) nodeData.value.localImages[i].imageUrl = convertFileSrc(img.imagePath)
      } else if (nodeData.value?.localImages?.[i]) {
        nodeData.value.localImages[i] = null
      }
    } else if (img.imageUrl?.startsWith('blob:')) {
      if (nodeData.value?.localImages?.[i]) nodeData.value.localImages[i] = null
    }
  }
})
</script>

<style>
@import '../../styles/node-ai-gen.css';
@import '../../styles/node-image.css';

.nb-textarea-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.gm-grid-9 {
  grid-template-columns: repeat(3, 1fr) !important;
  grid-template-rows: repeat(3, 1fr) !important;
}
</style>
