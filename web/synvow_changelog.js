import { $el } from "/scripts/ui.js";

const CHANGELOG = [
    {
        date: "2026/4/23",
        items: [
            {
                type: "fix",
                node: "全局",
                desc: "consumption_id 保持原始类型（integer），修复 or \"\" 导致的类型错误，涉及 nanobanana、veo3、sora2、seedance2、grok、gemini 节点"
            },
            {
                type: "fix",
                node: "nanobanana_synvow",
                desc: "轮询条件改为 if consumption_id is not None，避免 consumption_id=0 被错误跳过"
            },
            {
                type: "fix",
                node: "SynVow Gemini API 图生文",
                desc: "IS_CHANGED 改为基于参数哈希，seed 未变化时不再重复执行"
            },
            {
                type: "feat",
                node: "SynVow Gemini API 图生文",
                desc: "images_list 每张图独立并发任务；image_1~10 合并为单次请求一起发送给 Gemini"
            },
            {
                type: "feat",
                node: "SynVow GPT-Image-2",
                desc: "图像输入从 4 张扩展至 8 张（image1~image8）"
            },
            {
                type: "feat",
                node: "SynVow GPT-Image-2",
                desc: "新增 prompt 单条文本输入接口，与 prompts_list 区分；prompts_list 优先（多任务），prompt 为单任务"
            },
            {
                type: "fix",
                node: "SynVow GPT-Image-2",
                desc: "quality 参数修复：之前未传入后端，现已正确写入 payload；auto 时不传让后端使用默认值"
            },
            {
                type: "fix",
                node: "SynVow GPT-Image-2",
                desc: "日志 Base64 截断修复：images 列表中的 Base64 字符串也会被截断，不再刷屏"
            },
            {
                type: "feat",
                node: "SynVow GPT-Image-2",
                desc: "size 参数改为固定尺寸下拉选项（按官方文档推荐尺寸），移除 resolution + aspect_ratio 两个参数"
            },
        ]
    },
    {
        date: "2026/4/21",
        items: [
            {
                type: "feat",
                node: "SynVow GPT-Image-2",
                desc: "新增节点，支持文生图/图生图，异步提交+轮询，最多 4 张输入图，consumption_id 退费机制"
            },
            {
                type: "fix",
                node: "nanobanana_synvow",
                desc: "轮询时增加完整响应日志打印，便于排查状态字段异常"
            },
        ]
    },
];

const TYPE_BADGE = {
    feat: { label: "新增", color: "#2dd4bf" },
    fix:  { label: "修复", color: "#f59e0b" },
};

export function showChangelogDialog() {
    if (document.getElementById("sv-changelog-overlay")) return;

    const overlay = $el("div", {
        id: "sv-changelog-overlay",
        style: {
            position: "fixed", inset: "0", background: "rgba(0,0,0,0.6)",
            zIndex: "99999", display: "flex", alignItems: "center", justifyContent: "center"
        }
    });

    const close = () => overlay.remove();

    const rows = [];
    for (const section of CHANGELOG) {
        rows.push($el("div", {
            style: { fontSize: "13px", fontWeight: "bold", color: "#4a9eff", margin: "12px 0 6px" },
            textContent: `📅 ${section.date}`
        }));
        for (const item of section.items) {
            const badge = TYPE_BADGE[item.type] || { label: item.type, color: "#888" };
            rows.push($el("div", {
                style: {
                    display: "flex", alignItems: "flex-start", gap: "8px",
                    padding: "6px 0", borderBottom: "1px solid #2a2a2a"
                }
            }, [
                $el("span", {
                    style: {
                        flexShrink: "0", padding: "1px 6px", borderRadius: "4px",
                        fontSize: "11px", fontWeight: "bold",
                        background: badge.color + "22", color: badge.color, border: `1px solid ${badge.color}55`
                    },
                    textContent: badge.label
                }),
                $el("span", {
                    style: { flexShrink: "0", color: "#aaa", fontSize: "12px", paddingTop: "1px" },
                    textContent: item.node
                }),
                $el("span", {
                    style: { color: "#ddd", fontSize: "12px", lineHeight: "1.5", paddingTop: "1px" },
                    textContent: item.desc
                }),
            ]));
        }
    }

    const dialog = $el("div", {
        style: {
            background: "#1a1a1a", border: "1px solid #333", borderRadius: "10px",
            width: "680px", maxWidth: "92vw", maxHeight: "80vh",
            display: "flex", flexDirection: "column", overflow: "hidden"
        }
    }, [
        $el("div", {
            style: {
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "14px 18px", borderBottom: "1px solid #2a2a2a"
            }
        }, [
            $el("span", { style: { fontWeight: "bold", fontSize: "15px", color: "#fff" }, textContent: "📋 更新日志" }),
            $el("button", {
                style: {
                    background: "none", border: "none", color: "#aaa", fontSize: "18px",
                    cursor: "pointer", lineHeight: "1"
                },
                textContent: "✕",
                onclick: close
            })
        ]),
        $el("div", {
            style: { padding: "8px 18px 16px", overflowY: "auto", flex: "1" }
        }, rows)
    ]);

    overlay.appendChild(dialog);
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
    document.body.appendChild(overlay);
}
