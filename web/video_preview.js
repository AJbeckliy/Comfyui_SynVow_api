import { app } from '../../../scripts/app.js'
import { api } from '../../../scripts/api.js'

function fitHeight(node) {
    node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]])
    node?.graph?.setDirtyCanvas(true);
}

app.registerExtension({
    name: "SynVow.VideoPreview",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "SynVowGrokVideo"
            || nodeData.name === "SynVowGrokVideoBatch"
            || nodeData.name === "SynVowSora2Video" || nodeData.name === "SynVowSora2Video_Pro"
            || nodeData.name === "SynVowSora2Video_TBatch" || nodeData.name === "SynVowSora2Video_ProBatch"
            || nodeData.name === "SynVowVeo31Video" || nodeData.name === "SynVowVeo31VideoBatch") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                onNodeCreated?.apply(this, arguments);
                
                const previewNode = this;
                
                // 创建外层容器
                const element = document.createElement("div");
                
                const previewWidget = this.addDOMWidget("videopreview", "preview", element, {
                    serialize: false,
                    hideOnZoom: false,
                    getValue() { return element.value; },
                    setValue(v) { element.value = v; },
                });
                
                // 计算高度：支持多视频
                previewWidget.computeSize = function(width) {
                    if (!this.parentEl.hidden && this.totalHeight > 0) {
                        return [width, this.totalHeight];
                    }
                    return [width, -4];
                };
                
                previewWidget.parentEl = document.createElement("div");
                previewWidget.parentEl.className = "synvow_preview";
                previewWidget.parentEl.style.width = "100%";
                previewWidget.parentEl.style.display = "flex";
                previewWidget.parentEl.style.flexWrap = "wrap";
                previewWidget.parentEl.style.gap = "5px";
                element.appendChild(previewWidget.parentEl);
                
                // 存储视频元素列表
                previewWidget.videoElements = [];
                previewWidget.totalHeight = 0;
            };
            
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);
                
                const previewWidget = this.widgets?.find(w => w.name === "videopreview");
                if (!previewWidget) return;
                
                // 清空旧视频
                previewWidget.parentEl.innerHTML = "";
                previewWidget.videoElements = [];
                previewWidget.totalHeight = 0;
                
                if (!message?.gifs || message.gifs.length === 0) {
                    previewWidget.parentEl.hidden = true;
                    fitHeight(this);
                    return;
                }
                
                previewWidget.parentEl.hidden = false;
                const nodeWidth = this.size[0] - 20;
                let loadedCount = 0;
                const totalVideos = message.gifs.length;
                const previewNode = this;
                
                // 计算每个视频宽度：最多5列，超出换行
                const videoCount = message.gifs.filter(g => g && g.filename).length;
                const cols = Math.min(videoCount, 5);
                const videoWidth = `calc(${100/cols}% - ${cols > 1 ? '4px' : '0px'})`;
                
                message.gifs.forEach((gif, index) => {
                    if (!gif || !gif.filename) return;
                    
                    const videoContainer = document.createElement("div");
                    videoContainer.style.width = videoWidth;
                    videoContainer.style.marginBottom = "5px";
                    
                    const videoEl = document.createElement("video");
                    videoEl.controls = true;
                    videoEl.loop = true;
                    videoEl.muted = true;
                    videoEl.style.width = "100%";
                    
                    const params = new URLSearchParams({
                        filename: gif.filename,
                        subfolder: gif.subfolder || "",
                        type: gif.type || "output",
                        t: Date.now()
                    });
                    const videoUrl = api.apiURL('/view?' + params.toString());
                    
                    videoEl.addEventListener("loadedmetadata", () => {
                        loadedCount++;
                        // 所有视频加载完后计算总高度
                        if (loadedCount === totalVideos) {
                            // 等待DOM更新后计算高度
                            setTimeout(() => {
                                const containerRect = previewWidget.parentEl.getBoundingClientRect();
                                previewWidget.totalHeight = containerRect.height + 10;
                                fitHeight(previewNode);
                            }, 50);
                        }
                    });
                    
                    videoEl.addEventListener("error", () => {
                        videoContainer.style.display = "none";
                        loadedCount++;
                        if (loadedCount === totalVideos) {
                            fitHeight(previewNode);
                        }
                    });
                    
                    videoEl.src = videoUrl;
                    if (index === 0) {
                        videoEl.autoplay = true;
                    }
                    
                    videoContainer.appendChild(videoEl);
                    previewWidget.parentEl.appendChild(videoContainer);
                    previewWidget.videoElements.push(videoEl);
                });
                
                fitHeight(this);
            };
        }
    }
});
