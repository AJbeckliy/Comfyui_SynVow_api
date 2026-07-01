import { app } from "../../scripts/app.js";

const TARGET_NODE = "SynVowTransparentPngSavePreview";
const STALE_INPUTS = new Set(["images", "masks"]);
const STALE_WIDGETS = new Set(["preview_background", "save_preview_copy", "mask_mode"]);

function cleanTransparentSaveNode(node) {
    if (!node) return;

    if (Array.isArray(node.inputs)) {
        for (let index = node.inputs.length - 1; index >= 0; index--) {
            const input = node.inputs[index];
            if (input && STALE_INPUTS.has(input.name)) {
                node.removeInput(index);
            }
        }
    }

    if (Array.isArray(node.widgets)) {
        for (let index = node.widgets.length - 1; index >= 0; index--) {
            const widget = node.widgets[index];
            if (widget && STALE_WIDGETS.has(widget.name)) {
                widget.onRemove?.();
                node.widgets.splice(index, 1);
            }
        }
    }

    node.setSize?.(node.computeSize?.() || node.size);
    app.graph?.setDirtyCanvas(true, true);
}

app.registerExtension({
    name: "SynVow.TransparentPngSavePreview",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET_NODE) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = onNodeCreated?.apply(this, arguments);
            setTimeout(() => cleanTransparentSaveNode(this), 0);
            return result;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            const result = onConfigure?.apply(this, arguments);
            setTimeout(() => cleanTransparentSaveNode(this), 0);
            return result;
        };
    },
});
