import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function getResourceURL(subfolder, filename, type = "input") {
    return `/view?filename=${encodeURIComponent(filename)}&type=${type}&subfolder=${subfolder}&${app.getRandParam().substring(1)}`;
}

function splitFilePath(path) {
    const idx = path.lastIndexOf("/");
    return idx === -1 ? ["", path] : [path.substring(0, idx), path.substring(idx + 1)];
}

function updatePlayer(playerWidget, src) {
    if (!playerWidget?.element) return;
    playerWidget.element.src = src;
    if (src) {
        playerWidget.element.classList.remove("empty-audio-widget");
    } else {
        playerWidget.element.classList.add("empty-audio-widget");
    }
}

async function uploadAudioFile(comboWidget, playerWidget, file) {
    const body = new FormData();
    body.append("image", file);
    const resp = await api.fetchApi("/upload/image", { method: "POST", body });
    if (resp.status === 200) {
        const data = await resp.json();
        let name = data.name;
        if (data.subfolder) name = data.subfolder + "/" + name;
        if (!comboWidget.options.values.includes(name)) {
            comboWidget.options.values.push(name);
        }
        comboWidget.value = name;
        comboWidget.callback?.(name);
        const [subfolder, filename] = splitFilePath(name);
        updatePlayer(playerWidget, api.apiURL(getResourceURL(subfolder, filename)));
        return true;
    }
    console.error("Upload failed:", resp.status, resp.statusText);
    return false;
}

app.registerExtension({
    name: "SynVow.AudioUpload",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== "SynVowApiAudioLoader") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            const audioWidget = this.widgets?.find(w => w.name === "audio");
            if (!audioWidget) return;

            // 添加 audio 播放器 DOM widget
            const audioEl = document.createElement("audio");
            audioEl.controls = true;
            audioEl.classList.add("comfy-audio");
            audioEl.setAttribute("name", "media");
            const playerWidget = this.addDOMWidget("audioPlayer", "audioPlayer", audioEl, { serialize: false });
            playerWidget.serialize = false;

            // 初始化时根据当前 combo 值更新播放器
            const syncPlayer = () => {
                const val = audioWidget.value;
                if (val && val !== "") {
                    const [subfolder, filename] = splitFilePath(val);
                    updatePlayer(playerWidget, api.apiURL(getResourceURL(subfolder, filename)));
                } else {
                    updatePlayer(playerWidget, "");
                }
            };

            // combo 变化时同步播放器
            const origCallback = audioWidget.callback;
            audioWidget.callback = function (...args) {
                origCallback?.apply(this, args);
                syncPlayer();
            };

            // 工作流加载时同步
            const origConfigure = this.onConfigure;
            this.onConfigure = function (...args) {
                origConfigure?.apply(this, args);
                syncPlayer();
            };

            syncPlayer();

            // 添加上传按钮
            this.addWidget("button", "选择文件上传", "", () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "audio/*";
                input.onchange = async () => {
                    const file = input.files?.[0];
                    if (file) await uploadAudioFile(audioWidget, playerWidget, file);
                };
                input.click();
            }, { serialize: false });

            // 支持拖拽
            this.onDragOver = (e) => {
                return [...(e.dataTransfer?.items ?? [])].some(
                    i => i.kind === "file" && i.type.startsWith("audio/")
                );
            };
            this.onDragDrop = async (e) => {
                const files = [...(e.dataTransfer?.files ?? [])].filter(f => f.type.startsWith("audio/"));
                for (const f of files) await uploadAudioFile(audioWidget, playerWidget, f);
                return files.length > 0;
            };
        };
    },
});
