/**
 * SynVow Pool Filter
 * 1. 监听全局模式切换事件，动态刷新节点的模型下拉框
 * 2. 监听节点内 pool_mode widget 变化，动态刷新该节点的模型列表
 */
import { app } from "../../../scripts/app.js";

// 节点名 → 模型 widget 名称 + 类别
const NODE_MODEL_CONFIG = {
    "SynVowGeminiAPI":        { widget: "model_name", category: "chat" },
    "SynVowGeminiPromptGen":  { widget: "model_name", category: "chat" },
    "SynVowNanoBanana_T2I":   { widget: "model_select", category: "image", hasPool: true },
    "SynVowNanoBanana_I2I":   { widget: "model_select", category: "image", hasPool: true },
    "SynVowNanoBanana_Batch": { widget: "model_select", category: "image", hasPool: true },
};

// pool_mode 显示名 → 后端 mode 参数
const POOL_MODE_MAP = { "默认": "default", "优质": "stable" };

async function fetchModelsByMode(mode, category) {
    try {
        const res = await fetch(`/sv_api/models/by-mode?mode=${encodeURIComponent(mode)}&category=${encodeURIComponent(category)}`);
        if (!res.ok) return null;
        const data = await res.json();
        return data.models?.length ? data.models : null;
    } catch (e) {
        console.warn("[SynVow] fetchModelsByMode error:", e);
        return null;
    }
}

function updateNodeModelWidget(node, widgetName, models) {
    const w = node.widgets?.find(w => w.name === widgetName);
    if (!w) return;
    w.options.values = models;
    if (!models.includes(w.value)) w.value = models[0];
    node.setDirtyCanvas(true, true);
}

async function refreshAllNodes(mode) {
    const fetched = {};
    for (const node of app.graph._nodes || []) {
        const cfg = NODE_MODEL_CONFIG[node.comfyClass];
        if (!cfg) continue;
        if (!fetched[cfg.category]) {
            fetched[cfg.category] = await fetchModelsByMode(mode, cfg.category);
        }
        const models = fetched[cfg.category];
        if (models) updateNodeModelWidget(node, cfg.widget, models);
    }
}

/** 给单个节点的 pool_mode widget 绑定 change 回调 */
function bindPoolModeWidget(node, cfg) {
    const poolWidget = node.widgets?.find(w => w.name === "pool_mode");
    if (!poolWidget || poolWidget._sv_bound) return;
    poolWidget._sv_bound = true;

    const origCallback = poolWidget.callback;
    poolWidget.callback = async function (value) {
        if (origCallback) origCallback.call(this, value);
        const mode = POOL_MODE_MAP[value] || "default";
        const models = await fetchModelsByMode(mode, cfg.category);
        if (models) updateNodeModelWidget(node, cfg.widget, models);
    };
}

app.registerExtension({
    name: "SynVow.PoolFilter",

    async setup() {
        // 全局模式切换
        window.addEventListener("synvow_mode_changed", async (e) => {
            await refreshAllNodes(e.detail.mode);
        });

        const savedMode = localStorage.getItem("sv_mode") || "default";
        if (savedMode !== "default") {
            setTimeout(() => refreshAllNodes(savedMode), 2000);
        }
    },

    async nodeCreated(node) {
        const cfg = NODE_MODEL_CONFIG[node.comfyClass];
        if (!cfg?.hasPool) return;
        // 延迟绑定，等 widget 初始化完成
        setTimeout(() => bindPoolModeWidget(node, cfg), 100);
    },
});
