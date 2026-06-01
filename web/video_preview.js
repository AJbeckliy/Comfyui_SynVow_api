import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

app.registerExtension({
    name: "SynVow.VideoPreview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SynVowApiVideoPreview") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            const videoEl = document.createElement("video");
            videoEl.controls = true;
            videoEl.style.width = "100%";
            videoEl.style.display = "block";
            const previewWidget = this.addDOMWidget("videopreview", "preview", videoEl, { serialize: false });
            previewWidget.serialize = false;

            this.onExecuted = function (message) {
                if (!previewWidget.element) return;
                const gif = message?.gifs?.[0];
                if (!gif?.filename) {
                    previewWidget.element.src = "";
                    return;
                }
                const params = new URLSearchParams({
                    filename: gif.filename,
                    subfolder: gif.subfolder || "",
                    type: gif.type || "output",
                    t: Date.now()
                });
                previewWidget.element.src = api.apiURL('/view?' + params.toString());
            };
        };
    }
});
