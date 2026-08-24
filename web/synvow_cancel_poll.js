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

app.registerExtension({
    name: "SynVow.CancelPoll",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!SYNVOW_NODE_TYPES.has(nodeData.name)) return;
        const orig = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            orig?.apply(this, arguments);
            addCancelWidget(this);
        };
    },

    async setup() {
        setTimeout(() => {
            for (const node of app.graph._nodes || []) {
                if (SYNVOW_NODE_TYPES.has(node.type)) addCancelWidget(node);
            }
        }, 500);
    },

    afterConfigureGraph() {
        for (const node of app.graph._nodes || []) {
            if (SYNVOW_NODE_TYPES.has(node.type)) addCancelWidget(node);
        }
    },
});
