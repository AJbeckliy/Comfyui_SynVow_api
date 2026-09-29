const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

let extension;
const source = fs.readFileSync(path.join(__dirname, "../web/reference_layer_prompt.js"), "utf8")
    .replace(/^import .*;\r?\n/, "");
vm.runInNewContext(source, { app: { registerExtension: (value) => { extension = value; } } });

function nodeClass() {
    return class {
        configure(info) { this.loaded = info; return "configured"; }
        onSerialize(info) { info.other_extension_kept = true; return "serialized"; }
    };
}

(async () => {
    let checks = 0;
    for (const mode of ["自动规划(LLM)", "规则预设(不调用LLM)"]) {
        const Type = nodeClass();
        await extension.beforeRegisterNodeDef(Type, { name: "SynVowReferenceLayerPromptGenerator", input: { required: {} } });
        const info = { widgets_values: [mode, "4", "保留全部花朵", "GM3.6-flash-稳定", 42, "fixed"],
            widgets_values_named: { planner_mode: mode, layer_count: "2", seed: 999 },
            inputs: [{ name: "reference_image", link: 1 }] };
        const node = new Type();
        assert.equal(node.configure(info), "configured");
        assert.deepEqual(Array.from(node.loaded.widgets_values), ["4", "保留全部花朵", "GM3.6-flash-稳定", 42, "fixed"]);
        assert.equal(node.loaded.widgets_values_named.seed, 42);
        assert.equal(node.loaded.widgets_values_named.planner_mode, undefined);
        assert.equal(info.widgets_values.length, 6);
        assert.equal(info.widgets_values_named.seed, 999);
        assert.equal(node.loaded.inputs, info.inputs);
        node.configure(node.loaded);
        assert.equal(node.loaded.widgets_values.length, 5);
        const serialized = { widgets_values_named: { planner_mode: mode, seed: 42 } };
        assert.equal(node.onSerialize(serialized), "serialized");
        assert.equal(serialized.other_extension_kept, true);
        assert.equal(serialized.widgets_values_named.planner_mode, undefined);
        checks++;
    }
    const Fresh = nodeClass();
    await extension.beforeRegisterNodeDef(Fresh, { name: "SynVowReferenceLayerPromptGenerator", input: { required: {} } });
    const fresh = new Fresh();
    fresh.configure({ widgets_values: ["3", "", "model", 7, "randomize"] });
    assert.deepEqual(Array.from(fresh.loaded.widgets_values), ["3", "", "model", 7, "randomize"]);
    checks++;
    for (const data of [
        { name: "SynVowTransparentAssetPromptGenerator", input: { required: {} } },
        { name: "SynVowReferenceLayerPromptGenerator", input: { required: { planner_mode: ["COMBO"] } } },
    ]) {
        const Type = nodeClass();
        const original = Type.prototype.configure;
        await extension.beforeRegisterNodeDef(Type, data);
        assert.equal(Type.prototype.configure, original);
        checks++;
    }
    console.log(`${checks} UI migration cases passed`);
})().catch((error) => { console.error(error); process.exitCode = 1; });
