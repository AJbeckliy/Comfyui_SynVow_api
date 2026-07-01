import { app } from "../../scripts/app.js";

const TARGET_NODE = "SynVowGptImage2Alpha_TBatch";
const STALE_OUTPUTS = new Set(["images", "masks"]);
const CANONICAL_OUTPUTS = ["image_urls", "status"];
const CANCEL_WIDGET_NAME = "取消轮询";

function moveOutputLinks(node, fromIndex, toIndex) {
    const fromOutput = node.outputs?.[fromIndex];
    const toOutput = node.outputs?.[toIndex];
    if (!fromOutput || !toOutput || fromIndex === toIndex) return;

    const links = Array.isArray(fromOutput.links) ? [...fromOutput.links] : [];
    if (!links.length) return;
    if (!Array.isArray(toOutput.links)) toOutput.links = [];

    for (const linkId of links) {
        const link = app.graph?.links?.[linkId];
        if (link) {
            link.origin_slot = toIndex;
        }
        if (!toOutput.links.includes(linkId)) {
            toOutput.links.push(linkId);
        }
    }
    fromOutput.links = [];
}

function removeDuplicateOutput(node, name) {
    let indexes = node.outputs
        .map((output, index) => ({ output, index }))
        .filter(({ output }) => output?.name === name)
        .map(({ index }) => index);

    while (indexes.length > 1) {
        const keepIndex = indexes[0];
        const removeIndex = indexes[indexes.length - 1];
        moveOutputLinks(node, removeIndex, keepIndex);
        node.removeOutput(removeIndex);
        indexes = node.outputs
            .map((output, index) => ({ output, index }))
            .filter(({ output }) => output?.name === name)
            .map(({ index }) => index);
    }
}

function cleanAlphaNodeOutputs(node) {
    if (!node || !Array.isArray(node.outputs)) return;

    for (let index = node.outputs.length - 1; index >= 0; index--) {
        const output = node.outputs[index];
        if (output && STALE_OUTPUTS.has(output.name)) {
            node.removeOutput(index);
        }
    }

    for (const name of CANONICAL_OUTPUTS) {
        removeDuplicateOutput(node, name);
    }

    node.setSize?.(node.computeSize?.() || node.size);
    app.graph?.setDirtyCanvas(true, true);
}

function addAlphaCancelWidget(node) {
    if (!node || node.widgets?.find((widget) => widget.name === CANCEL_WIDGET_NAME)) return;

    const button = node.addWidget("button", CANCEL_WIDGET_NAME, null, () => {
        button.value = "已发送中断信号";
        fetch("/synvow/alpha/cancel", { method: "POST" }).catch((error) => {
            console.error("[SynVow] alpha cancel failed:", error);
        });
        fetch("/interrupt", { method: "POST" }).catch((error) => {
            console.error("[SynVow] interrupt failed:", error);
        });
        setTimeout(() => {
            button.value = CANCEL_WIDGET_NAME;
        }, 3000);
    });
    button.serialize = false;
}

function refreshAlphaNode(node) {
    cleanAlphaNodeOutputs(node);
    addAlphaCancelWidget(node);
}

app.registerExtension({
    name: "SynVow.GptImage2AlphaUrlOnly",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_NODE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            setTimeout(() => refreshAlphaNode(this), 0);
            return result;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            setTimeout(() => refreshAlphaNode(this), 0);
            return result;
        };
    },

    async setup() {
        setTimeout(() => {
            for (const node of app.graph?._nodes || []) {
                if (node.type === TARGET_NODE) refreshAlphaNode(node);
            }
        }, 500);
    },

    afterConfigureGraph() {
        for (const node of app.graph?._nodes || []) {
            if (node.type === TARGET_NODE) refreshAlphaNode(node);
        }
    },
});
