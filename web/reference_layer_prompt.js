import { app } from "../../scripts/app.js";

const TARGET = "SynVowReferenceLayerPromptGenerator";
const LEGACY_MODES = new Set(["自动规划(LLM)", "规则预设(不调用LLM)"]);
const WIDGET_NAMES = ["layer_count", "custom_prompt", "llm_model", "seed", "control_after_generate"];

function migrateInfo(info) {
    if (!info || !Array.isArray(info.widgets_values)) return info;
    const values = LEGACY_MODES.has(info.widgets_values[0])
        ? info.widgets_values.slice(1)
        : [...info.widgets_values];
    const migrated = { ...info, widgets_values: values };
    if (info.widgets_values_named) {
        migrated.widgets_values_named = { ...info.widgets_values_named };
        delete migrated.widgets_values_named.planner_mode;
        // Serialized widget values are authoritative; older named metadata may be stale.
        WIDGET_NAMES.forEach((name, index) => {
            if (index < values.length) migrated.widgets_values_named[name] = values[index];
        });
    }
    return migrated;
}

app.registerExtension({
    name: "SynVow.ReferenceLayerLlmOnly",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== TARGET || nodeData.input?.required?.planner_mode) return;
        const configure = nodeType.prototype.configure;
        if (typeof configure !== "function") return;
        nodeType.prototype.configure = function (info, ...args) {
            return configure.call(this, migrateInfo(info), ...args);
        };
        const serialize = nodeType.prototype.onSerialize;
        nodeType.prototype.onSerialize = function (info, ...args) {
            const result = serialize?.call(this, info, ...args);
            if (info.widgets_values_named) delete info.widgets_values_named.planner_mode;
            return result;
        };
    },
});
