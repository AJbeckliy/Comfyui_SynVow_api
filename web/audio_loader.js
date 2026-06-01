import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { mediaValueToURL, uploadMediaFile, bindCropPreview } from "./dom.js";

function updatePlayer(playerWidget, src) {
    if (!playerWidget?.element) return;
    playerWidget.element.src = src;
    playerWidget.element.classList.toggle("empty-audio-widget", !src);
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

            const audioEl = document.createElement("audio");
            audioEl.controls = true;
            audioEl.classList.add("comfy-audio");
            audioEl.setAttribute("name", "media");
            const playerWidget = this.addDOMWidget("audioPlayer", "audioPlayer", audioEl, { serialize: false });
            playerWidget.serialize = false;

            bindCropPreview(this, audioEl);

            const syncPlayer = () => updatePlayer(playerWidget, mediaValueToURL(api, app, audioWidget.value));

            const origCallback = audioWidget.callback;
            audioWidget.callback = function (...args) {
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
                input.accept = "audio/*";
                input.onchange = async () => {
                    const file = input.files?.[0];
                    if (file) await uploadMediaFile(api, app, audioWidget, file, src => updatePlayer(playerWidget, src));
                };
                input.click();
            }, { serialize: false });

            this.onDragOver = (e) => [...(e.dataTransfer?.items ?? [])].some(
                i => i.kind === "file" && i.type.startsWith("audio/")
            );
            this.onDragDrop = async (e) => {
                const files = [...(e.dataTransfer?.files ?? [])].filter(f => f.type.startsWith("audio/"));
                for (const f of files) await uploadMediaFile(api, app, audioWidget, f, src => updatePlayer(playerWidget, src));
                return files.length > 0;
            };
        };
    },
});
