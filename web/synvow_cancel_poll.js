/**
 * SynVow 节点执行中在节点上显示取消轮询按钮
 * 点击后调用 /interrupt 中断 ComfyUI 队列，后台 API 继续运行
 */
import { app } from "../../../scripts/app.js";

const SYNVOW_NODE_TYPES = new Set([
    "SynVowSeedance",
    "SynVowSeedance2Video",
    "SynVowSeedance25",
    "SynVowWanVideo",
    "SynVowGrokVideo",
    "SynVowVeo31",
    "SynVowOmniFlash",
    "SynVowMiniMaxTextToVideo",
    "SynVowMiniMaxFirstLastFrame",
    "SynVowMiniMaxReferenceToVideo",
    "SynVowSunoInspire",
    "SynVowSunoCustom",
    "SynVowDoubaoAudio",
    "SynVowGptImage2",
    "SynVowGptImage2_TBatch",
    "SynVowGptImage2_IBatch",
    "SynVowGptImage2_TIBatch",
    "SynVowGptImage2ProductStudio",
    "SynVowNanoBanana",
    "SynVowNanoBanana_TBatch",
    "SynVowNanoBanana_IBatch",
    "SynVowNanoBanana_TIBatch",
    "SynVowJimeng",
    "SynVowJimeng_TBatch",
    "SynVowJimeng_IBatch",
    "SynVowJimeng_TIBatch",
    "SynVowGkImage",
    "SynVowGkImage_TBatch",
    "SynVowGkImage_IBatch",
    "SynVowGkImage_TIBatch",
    "SynVowGkImage20",
    "SynVowGkImage20_TBatch",
    "SynVowGkImage20_IBatch",
    "SynVowGkImage20_TIBatch",
    "SynVowMidjourneyText",
    "SynVowMidjourneyBlend",
    "SynVowMidjourneyEdit",
]);

function addCancelWidget(node) {
    if (node.widgets?.find(w => w.name === "取消轮询")) return;
    const btn = node.addWidget("button", "取消轮询", null, () => {
        btn.value = "已发送中断信号";
        fetch("/interrupt", { method: "POST" }).catch(e => {
            console.error("[SynVow] interrupt failed:", e);
        });
        setTimeout(() => { btn.value = "取消轮询"; }, 3000);
    });
    btn.serialize = false;
}

const SEEDANCE25_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"];
const SEEDANCE25_DJ_RATIOS = ["16:9", "9:16"];
const OMNI_RESOLUTIONS = ["720p", "1080p", "4k"];
const OMNI_11_RESOLUTIONS = ["360p", "720p", "1080p", "4k"];
const GPT_IMAGE_RESOLUTIONS = ["1K", "2K", "4K"];

function bindModelCombo(node, types, modelName, comboName, pickOpts, fallback) {
    const match = typeof types === "function" ? types(node.type) : node.type === types;
    const key = `_svBind_${modelName}_${comboName}`;
    if (!match || node[key]) return;
    const modelW = node.widgets?.find(w => w.name === modelName);
    const comboW = node.widgets?.find(w => w.name === comboName);
    if (!modelW || !comboW) return;
    node[key] = true;

    const apply = () => {
        const opts = pickOpts(String(modelW.value || ""));
        if (comboW.options) comboW.options.values = opts;
        if (!opts.includes(comboW.value)) comboW.value = fallback ? fallback(opts) : opts[0];
    };
    const prev = modelW.callback;
    modelW.callback = function () {
        const r = prev?.apply(this, arguments);
        apply();
        return r;
    };
    apply();
}

function bindWidgetOptions(node) {
    bindModelCombo(node, "SynVowSeedance25", "model", "ratio", v =>
        (v === "sd2-5-dj" || v.includes("低价")) ? SEEDANCE25_DJ_RATIOS : SEEDANCE25_RATIOS);
    bindModelCombo(node, "SynVowOmniFlash", "model", "resolution", v => {
        if (v === "omni-1.1-flash" || v.includes("O-1.1")) return OMNI_11_RESOLUTIONS;
        if (v === "omni-flash-preview" || v.includes("O-flash-preview")) return ["720p"];
        return OMNI_RESOLUTIONS;
    }, opts => (opts.includes("720p") ? "720p" : opts[0]));
    bindModelCombo(node, t => String(t || "").startsWith("SynVowGptImage2"), "model_type", "resolution", v =>
        v.includes("1k-") ? ["1K"] : GPT_IMAGE_RESOLUTIONS);
}

function enhanceNode(node) {
    addCancelWidget(node);
    bindWidgetOptions(node);
}

app.registerExtension({
    name: "SynVow.CancelPoll",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!SYNVOW_NODE_TYPES.has(nodeData.name)) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            orig?.apply(this, arguments);
            enhanceNode(this);
        };
    },

    async setup() {
        setTimeout(() => {
            for (const node of app.graph._nodes || []) {
                if (SYNVOW_NODE_TYPES.has(node.type)) enhanceNode(node);
            }
        }, 500);
    },

    afterConfigureGraph() {
        for (const node of app.graph._nodes || []) {
            if (SYNVOW_NODE_TYPES.has(node.type)) enhanceNode(node);
        }
    },
});
