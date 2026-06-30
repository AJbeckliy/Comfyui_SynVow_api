/**
 * ComfyUI Text List Editor Extension
 */
import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// 工具函数
const cleanTextWidgets = (node) => {
    for (let i = node.widgets.length - 1; i >= 0; i--) {
        const widget = node.widgets[i];
        if (widget.name && widget.name.startsWith('text_item_')) {
            widget.onRemove?.();
            node.widgets.splice(i, 1);
        }
    }
};

const createTextWidgets = (node, texts) => {
    texts.forEach((text, index) => {
        const widgetName = `text_item_${index}`;
        const textValue = String(text || "").trim();
        try {
            const widgetData = ComfyWidgets.STRING(
                node,
                widgetName,
                ["STRING", { multiline: true, default: textValue }],
                app
            );
            if (widgetData && widgetData.widget) {
                widgetData.widget.value = textValue;
                widgetData.widget.serialize = false;
            }
        } catch (error) {
            console.error(`TextListEditor: Failed to create widget ${index + 1}:`, error);
        }
    });
};

const collectEditedTexts = (node) => {
    const editedTexts = [];
    const textWidgets = node.widgets
        .filter(w => w && w.name && w.name.startsWith('text_item_'))
        .map(w => {
            const parts = w.name.split('_');
            const index = parts.length >= 3 ? parseInt(parts[2]) : -1;
            return { widget: w, index: isNaN(index) ? -1 : index };
        })
        .sort((a, b) => a.index - b.index);

    textWidgets.forEach(({ widget }) => {
        editedTexts.push(String(widget.value || "").trim());
    });
    return editedTexts;
};


const sendRequest = async (endpoint, data) => {
    return api.fetchApi(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
};

app.registerExtension({
    name: "Comfy.TextListEditor",

    async setup() {
        api.addEventListener("text_list_edit_session", (event) => {
            const { session_id, node_id, texts } = event.detail;
            const node = app.graph._nodes.find(n => n.id == node_id);
            if (!node || !texts || texts.length === 0) return;

            // 清理旧的 widgets
            cleanTextWidgets(node);
            app.graph.setDirtyCanvas(true, true);

            node.session_id = session_id;
            node.original_texts = texts;

            // 延迟创建新 widgets
            setTimeout(() => {
                createTextWidgets(node, texts);
                app.graph.setDirtyCanvas(true, true);
            }, 50);
        });
    },

    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "SynVowApiTextListEditor") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const result = onNodeCreated?.apply(this, arguments);

            this.session_id = null;
            this.original_texts = [];

            const originalOnRemoved = this.onRemoved;
            this.onRemoved = function() {
                cleanTextWidgets(this);
                if (originalOnRemoved) originalOnRemoved.call(this);
            };

            // 调整大小时强制重绘
            const originalOnResize = this.onResize;
            this.onResize = function(size) {
                if (originalOnResize) originalOnResize.call(this, size);
                app.graph.setDirtyCanvas(true, true);
            };

            // Continue button
            const continueButton = this.addWidget("button", "Continue", null, async () => {
                if (!this.session_id) {
                    alert('Please run the workflow first');
                    return;
                }

                const editedTexts = collectEditedTexts(this);
                if (editedTexts.length === 0) {
                    alert('No editable text found');
                    return;
                }

                try {
                    const response = await sendRequest('/text_list_edit/confirm', {
                        session_id: this.session_id,
                        edited_texts: editedTexts
                    });

                    if (response.ok) {
                        app.graph.setDirtyCanvas(true);
                    } else {
                        alert('Confirm failed, please retry');
                    }
                } catch (error) {
                    console.error('Confirm failed:', error);
                    alert('Confirm failed: ' + error.message);
                }
            });
            continueButton.serialize = false;

            // Cancel button
            const cancelButton = this.addWidget("button", "Cancel", null, async () => {
                if (this.session_id) {
                    try {
                        await sendRequest('/text_list_edit/cancel', {
                            session_id: this.session_id
                        });
                    } catch (error) {
                        console.error('Cancel request failed:', error);
                    }
                }

                await api.interrupt();
                this.session_id = null;
                app.graph.setDirtyCanvas(true);
            });
            cancelButton.serialize = false;

            return result;
        };
    }
});
