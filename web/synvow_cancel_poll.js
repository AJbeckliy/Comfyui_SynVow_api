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
    "SynVowSuno6",
    "SynVowDoubaoAudio",
    "SynVowGptImage2",
    "SynVowGptImage2_TBatch",
    "SynVowGptImage2_IBatch",
    "SynVowGptImage2_TIBatch",
    "SynVowGptImage2ProductStudio",
    "SynVowGptImage2Alpha_TBatch",
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
const OMNI_11_RESOLUTIONS = ["360p", "720p", "1080p", "4k"];
const OMNI_RESOLUTIONS = OMNI_11_RESOLUTIONS.slice(1);
const GPT_IMAGE_RESOLUTIONS = ["1K", "2K", "4K"];
const GPT_Q6 = ["auto", "low", "medium", "high", "xhigh", "max"];
const GPT_Q4 = GPT_Q6.slice(0, 4);
const GPT_ASPECTS = [
    "auto", "1:1", "16:9", "9:16", "4:3", "3:4", "5:4", "4:5",
    "3:2", "2:3", "3:1", "1:3", "2:1", "1:2", "21:9", "9:21",
];
const GPT_WD_ASPECTS = [
    "auto", "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "5:4", "4:5", "21:9",
];
const N2_ULTRA = ["1:4", "4:1", "1:8", "8:1"];
const N2_ASPECTS = [
    "auto", "1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "5:4", "4:5", "21:9", ...N2_ULTRA,
];
const NPRO_ASPECTS = [
    "auto", "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
];

function widget(node, name) {
    return node.widgets?.find(w => w.name === name);
}

function setCombo(w, opts, prefer) {
    if (!w) return;
    if (w.options) w.options.values = opts;
    if (!opts.includes(w.value)) w.value = opts.includes(prefer) ? prefer : opts[0];
}

function setHidden(obj, hidden) {
    if (obj) obj.hidden = hidden;
}

function bindByWidgets(node, names, apply) {
    const key = `_svBind_${names.join("_")}`;
    if (node[key]) return;
    const ws = names.map(n => widget(node, n));
    if (!ws[0]) return;
    node[key] = true;
    const run = () => {
        apply();
        node.setDirtyCanvas?.(true, true);
    };
    for (const w of ws) {
        if (!w) continue;
        const prev = w.callback;
        w.callback = function () {
            const r = prev?.apply(this, arguments);
            run();
            return r;
        };
    }
    run();
}

function bindByModel(node, modelName, apply) {
    bindByWidgets(node, [modelName], () => {
        apply(String(widget(node, modelName)?.value || ""));
    });
}

function bindWidgetOptions(node) {
    const t = String(node.type || "");
    if (t === "SynVowSeedance25") {
        bindByModel(node, "model", v => {
            setCombo(widget(node, "ratio"),
                (v === "sd2-5-dj" || v.includes("低价")) ? SEEDANCE25_DJ_RATIOS : SEEDANCE25_RATIOS);
        });
        return;
    }
    if (t === "SynVowSeedance") {
        bindByModel(node, "model", v => {
            setCombo(widget(node, "resolution"),
                v === "seedance-2.0" ? ["480p", "720p", "1080p"] : ["480p", "720p"]);
        });
        return;
    }
    if (t.startsWith("SynVowJimeng")) {
        bindByModel(node, "model_type", v => {
            setCombo(widget(node, "resolution"),
                v.includes("pro") || v.includes("Pro") ? ["1K", "2K"] : ["2K", "3K", "4K"]);
        });
        return;
    }
    if (t === "SynVowOmniFlash") {
        bindByModel(node, "model", v => {
            const v11 = v === "omni-1.1-flash" || v.includes("O-1.1");
            const preview = v === "omni-flash-preview" || v.includes("O-flash-preview");
            const resW = widget(node, "resolution");
            setCombo(resW, v11 ? OMNI_11_RESOLUTIONS : preview ? ["720p"] : OMNI_RESOLUTIONS, "720p");
            setHidden(widget(node, "mode"), preview || v11);
            setHidden(widget(node, "duration"), preview || v11);
            setHidden(resW, preview);
        });
        return;
    }
    if (t.startsWith("SynVowGptImage2")) {
        bindByModel(node, "model_type", v => {
            const lock1k = v.includes("1k-");
            const wd = v === "gpt-image-2.5-wd" || v.includes("PT2.5-稳定");
            const pt25 = v.includes("gpt-image-2.5") || v.includes("PT2.5");
            const is1k2609 = v.includes("1k-2609");
            const g2stable = v === "gpt-image-2-稳定" || v.includes("全能G2-稳定");
            const showStyle = pt25 && !is1k2609;
            const showQuality = !g2stable && !is1k2609 && !wd;
            const qW = widget(node, "quality");
            const aW = widget(node, "aspect_ratio");
            setCombo(widget(node, "resolution"), lock1k ? ["1K"] : GPT_IMAGE_RESOLUTIONS, "1K");
            setCombo(qW, pt25 && showQuality ? GPT_Q6 : GPT_Q4, "auto");
            setCombo(aW, wd ? GPT_WD_ASPECTS : GPT_ASPECTS, aW?.value === "auto" ? "auto" : "1:1");
            setHidden(widget(node, "gpt_style"), !showStyle);
            setHidden(qW, !showQuality);
            setHidden(widget(node, "transparent"), !(showStyle && !lock1k && !wd));
        });
        return;
    }
    if (t.startsWith("SynVowNanoBanana")) {
        bindByModel(node, "model_type", v => {
            const pro = /pro/i.test(v);
            const noUltra = v.includes("lite-2607");
            const opts = pro ? NPRO_ASPECTS : noUltra ? N2_ASPECTS.filter(r => !N2_ULTRA.includes(r)) : N2_ASPECTS;
            setCombo(widget(node, "aspect_ratio"), opts, "1:1");
        });
        return;
    }
    if (t === "SynVowSuno6") {
        bindByWidgets(node, ["task_kind", "mode", "instrumental"], () => {
            const kind = String(widget(node, "task_kind")?.value || "");
            const custom = String(widget(node, "mode")?.value || "") === "自定义";
            const extend = kind === "延长";
            const inst = !!widget(node, "instrumental")?.value;
            setHidden(widget(node, "continue_at"), !extend);
            setHidden(widget(node, "instrumental"), extend);
            setHidden(widget(node, "vocal_gender"), !(extend || !inst));
            for (const name of ["duration", "title", "tags", "negative_tags"]) {
                setHidden(widget(node, name), !custom);
            }
            setHidden(node.inputs?.find(s => s.name === "audio_path"), !(kind === "翻唱" || extend));
        });
    }
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
