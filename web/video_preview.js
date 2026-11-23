import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

app.registerExtension({
    name: "SynVow.VideoPreview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SynVowApiVideoPreview") return;

        const origCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            origCreated?.apply(this, arguments);

            const box = document.createElement("div");
            const bar = document.createElement("div");
            bar.style.cssText = "display:none;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;";
            const prev = document.createElement("button");
            const next = document.createElement("button");
            const label = document.createElement("span");
            prev.textContent = "上一条";
            next.textContent = "下一条";
            label.style.color = "#ccc";
            bar.append(prev, label, next);
            const videoEl = document.createElement("video");
            videoEl.controls = true;
            videoEl.style.width = "100%";
            videoEl.style.display = "block";
            box.append(bar, videoEl);
            const previewWidget = this.addDOMWidget("videopreview", "preview", box, { serialize: false });
            previewWidget.serialize = false;
            let gifs = [];
            let index = 0;

            const show = (i) => {
                if (!gifs.length) {
                    videoEl.removeAttribute("src");
                    videoEl.load();
                    bar.style.display = "none";
                    return;
                }
                index = (i + gifs.length) % gifs.length;
                const gif = gifs[index];
                const params = new URLSearchParams({
                    filename: gif.filename,
                    subfolder: gif.subfolder || "",
                    type: gif.type || "output",
                    t: Date.now()
                });
                videoEl.src = api.apiURL("/view?" + params.toString());
                label.textContent = `${index + 1} / ${gifs.length}`;
                bar.style.display = gifs.length > 1 ? "flex" : "none";
            };
            prev.onclick = () => show(index - 1);
            next.onclick = () => show(index + 1);

            this.onExecuted = function (message) {
                gifs = message?.gifs || [];
                show(0);
            };
        };
    }
});
