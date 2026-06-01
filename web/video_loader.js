import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { mediaValueToURL, uploadMediaFile, bindCropPreview } from "./dom.js";

function updatePlayer(playerWidget, src) {
    if (!playerWidget?.element) return;
    playerWidget.element.src = src;
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

            const videoEl = document.createElement("video");
            videoEl.controls = true;
            videoEl.classList.add("comfy-video");
            videoEl.style.width = "100%";
            const playerWidget = this.addDOMWidget("videoPlayer", "videoPlayer", videoEl, { serialize: false });
            playerWidget.serialize = false;

            bindCropPreview(this, videoEl);

            const syncPlayer = () => updatePlayer(playerWidget, mediaValueToURL(api, app, videoWidget.value));

            const origCallback = videoWidget.callback;
            videoWidget.callback = function (...args) {
                origCallback?.apply(this, args);
                syncPlayer();
            };

            const origConfigure = this.onConfigure;
            this.onConfigure = function (...args) {
                origConfigure?.apply(this, args);
                syncPlayer();
            };

            syncPlayer();

            this.addWidget("button", "选择文件上传", "", () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = "video/*";
                input.onchange = async () => {
                    const file = input.files?.[0];
                    if (file) await uploadMediaFile(api, app, videoWidget, file, src => updatePlayer(playerWidget, src));
                };
                input.click();
            }, { serialize: false });

            this.onDragOver = (e) => [...(e.dataTransfer?.items ?? [])].some(
                i => i.kind === "file" && i.type.startsWith("video/")
            );
            this.onDragDrop = async (e) => {
                const files = [...(e.dataTransfer?.files ?? [])].filter(f => f.type.startsWith("video/"));
                for (const f of files) await uploadMediaFile(api, app, videoWidget, f, src => updatePlayer(playerWidget, src));
                return files.length > 0;
            };
        };
    },
});
