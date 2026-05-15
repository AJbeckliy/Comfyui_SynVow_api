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
}

async function uploadVideoFile(comboWidget, playerWidget, file) {
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
    name: "SynVow.VideoUpload",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData?.name !== "SynVowApiVideoLoader") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            const videoWidget = this.widgets?.find(w => w.name === "video");
            if (!videoWidget) return;

            // 添加 video 播放器 DOM widget
            const videoEl = document.createElement("video");
            videoEl.controls = true;
            videoEl.classList.add("comfy-video");
            videoEl.style.width = "100%";
            const playerWidget = this.addDOMWidget("videoPlayer", "videoPlayer", videoEl, { serialize: false });
            playerWidget.serialize = false;

            // 根据当前 combo 值更新播放器
            const syncPlayer = () => {
                const val = videoWidget.value;
                if (val && val !== "") {
                    const [subfolder, filename] = splitFilePath(val);
                    updatePlayer(playerWidget, api.apiURL(getResourceURL(subfolder, filename)));
                } else {
                    updatePlayer(playerWidget, "");
                }
            };

            // combo 变化时同步播放器
            const origCallback = videoWidget.callback;
            videoWidget.callback = function (...args) {
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
                input.accept = "video/*";
                input.onchange = async () => {
                    const file = input.files?.[0];
                    if (file) await uploadVideoFile(videoWidget, playerWidget, file);
                };
                input.click();
            }, { serialize: false });

            // 支持拖拽
            this.onDragOver = (e) => {
                return [...(e.dataTransfer?.items ?? [])].some(
                    i => i.kind === "file" && i.type.startsWith("video/")
                );
            };
            this.onDragDrop = async (e) => {
                const files = [...(e.dataTransfer?.files ?? [])].filter(f => f.type.startsWith("video/"));
                for (const f of files) await uploadVideoFile(videoWidget, playerWidget, f);
                return files.length > 0;
            };
        };
    },
});
