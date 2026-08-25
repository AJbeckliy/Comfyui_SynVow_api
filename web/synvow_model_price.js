/**
 * 模型价格对话框
 */
import { $el, injectStyle, API_BASE, paginationCss } from "./dom.js";

const PRICE_TAG_TABS = [
    { id: 1, label: "文本" },
    { id: 4, label: "图像" },
    { id: 6, label: "视频" },
    { id: 5, label: "音频" },
    { id: 8, label: "解析" },
    { id: 7, label: "其它" },
];

let priceDialog = null;
let currentPage = 1;
let currentTagId = 1;

function normalizeModelListPayload(payload, fallbackPage, pageSize) {
    const data = payload?.data;
    const list = Array.isArray(data) ? data : (data?.list ?? []);
    const total = Number(data?.total ?? list.length ?? 0);
    return {
        items: list,
        total,
        totalPages: Number(data?.total_pages ?? (Math.ceil(total / pageSize) || 1)),
        page: Number(data?.page ?? fallbackPage),
    };
}

export function showModelPriceDialog() {
    if (priceDialog) { priceDialog.remove(); priceDialog = null; }
    currentPage = 1;
    currentTagId = 1;

    const oldStyle = document.getElementById("sv-price-style");
    if (oldStyle) oldStyle.remove();
    injectStyle("sv-price-style", `
        .sv-mp-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-mp-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:14px; padding:20px 22px 16px; width:min(1180px,92vw); height:82vh; position:relative; display:flex; flex-direction:column; box-shadow:0 24px 80px rgba(0,0,0,.45); border:1px solid rgba(45,212,191,.16); }
        .sv-mp-title { color:#2dd4bf; font-size:17px; font-weight:bold; margin-bottom:12px; display:flex; align-items:center; gap:8px; flex-shrink:0; }
        .sv-mp-close { position:absolute; top:12px; right:14px; background:none; border:none; color:#667788; font-size:22px; cursor:pointer; }
        .sv-mp-close:hover { color:white; }
        .sv-mp-tag-bar { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; flex-shrink:0; }
        .sv-mp-tag-btn { border:1px solid rgba(80,105,125,.45); border-radius:999px; background:rgba(16,41,56,.55); color:#9aabba; padding:5px 12px; font-size:13px; cursor:pointer; }
        .sv-mp-tag-btn:hover { color:#fff; border-color:#2dd4bf; }
        .sv-mp-tag-btn.active { border-color:#2dd4bf; background:rgba(45,212,191,.14); color:#2dd4bf; font-weight:600; }
        .sv-mp-content { flex:1; min-height:0; overflow-y:auto; margin-bottom:10px; }
        .sv-mp-grid { display:grid; grid-template-columns:repeat(5,1fr); grid-template-rows:repeat(5,1fr); gap:8px; height:100%; }
        .sv-mp-grid.loading { opacity:0.45; pointer-events:none; transition:opacity .15s; }
        .sv-mp-card { background:rgba(16,41,56,.55); border:1px solid rgba(80,105,125,.35); border-radius:8px; padding:10px 12px; display:flex; flex-direction:column; gap:8px; min-height:0; }
        .sv-mp-card-head { display:flex; justify-content:space-between; align-items:flex-start; gap:6px; }
        .sv-mp-name { color:#fff; font-weight:700; font-size:13px; line-height:1.25; }
        .sv-mp-tags-cell { color:#8899aa; font-size:11px; margin-top:2px; line-height:1.2; }
        .sv-mp-price-list { display:flex; flex-direction:column; gap:3px; flex:1; justify-content:flex-end; }
        .sv-mp-price-row { display:flex; align-items:center; justify-content:space-between; gap:4px; background:rgba(45,212,191,.05); border-radius:4px; padding:2px 7px; line-height:1.35; }
        .sv-mp-price-name { color:#9aabba; font-size:11px; }
        .sv-mp-price-val { color:#2dd4bf; font-weight:700; font-size:12px; white-space:nowrap; }
        .sv-mp-price-empty { color:#667788; font-size:11px; }
        .sv-mp-status-on  { color:#22c55e; font-size:11px; flex-shrink:0; }
        .sv-mp-status-off { color:#ef4444; font-size:11px; flex-shrink:0; }
        .sv-mp-empty { text-align:center; color:#667788; padding:28px; min-height:100%; display:flex; align-items:center; justify-content:center; }
        .sv-mp-pagination { flex-shrink:0; }
    ` + paginationCss("sv-mp"));

    const contentDiv = $el("div.sv-mp-content", {}, [
        $el("div.sv-mp-empty", { textContent: "加载中..." })
    ]);
    const prevBtn  = $el("button.sv-mp-page-btn", { textContent: "上一页", onclick: () => loadPage(currentPage - 1) });
    const nextBtn  = $el("button.sv-mp-page-btn", { textContent: "下一页", onclick: () => loadPage(currentPage + 1) });
    const pageInfo = $el("span.sv-mp-page-info");

    const tagButtons = PRICE_TAG_TABS.map((tab) => $el("button.sv-mp-tag-btn", {
        textContent: tab.label,
        onclick: () => selectTag(tab.id),
    }));
    const syncTagButtons = () => {
        tagButtons.forEach((btn, i) => {
            btn.classList.toggle("active", PRICE_TAG_TABS[i].id === currentTagId);
        });
    };
    const selectTag = (id) => {
        if (currentTagId === id) return;
        currentTagId = id;
        syncTagButtons();
        contentDiv.replaceChildren($el("div.sv-mp-empty", { textContent: "加载中..." }));
        loadPage(1);
    };
    syncTagButtons();

    priceDialog = $el("div.sv-mp-overlay", {
        onclick: (e) => { if (e.target === priceDialog) priceDialog.remove(); }
    }, [
        $el("div.sv-mp-dialog", {}, [
            $el("button.sv-mp-close", { textContent: "×", onclick: () => priceDialog.remove() }),
            $el("div.sv-mp-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg> 模型价格` }),
            $el("div.sv-mp-tag-bar", {}, tagButtons),
            contentDiv,
            $el("div.sv-mp-pagination", {}, [prevBtn, pageInfo, nextBtn])
        ])
    ]);

    document.body.appendChild(priceDialog);
    loadPage(1);

    async function loadPage(page) {
        page = Math.max(1, parseInt(page) || 1);

        const grid = contentDiv.querySelector(".sv-mp-grid");
        if (grid) grid.classList.add("loading");
        prevBtn.disabled = true;
        nextBtn.disabled = true;

        try {
            const pageSize = 25;
            const params = new URLSearchParams({
                page: String(page), page_size: String(pageSize),
                sort_by: "sort", sort_order: "ASC", tag_id: String(currentTagId),
            });
            const res  = await fetch(`${API_BASE}/models/public-list?${params.toString()}`);
            const text = await res.text();
            if (!text) throw new Error(`接口无响应(${res.status})`);
            const data = JSON.parse(text);
            if (data.code === 200 && data.data) {
                const { items, total, totalPages, page: normalizedPage } = normalizeModelListPayload(data, page, pageSize);
                currentPage = normalizedPage;

                if (items.length === 0) {
                    contentDiv.replaceChildren($el("div.sv-mp-empty", { textContent: "暂无价格数据" }));
                } else {
                    const gridEl = $el("div.sv-mp-grid");
                    for (const model of items) {
                        const displayName = model.custom_name || model.name || "-";
                        const tags = (model.tags || []).map(t => t.name).filter(Boolean);
                        const priceDetails = model.price_details || [];

                        const priceList = $el("div.sv-mp-price-list");
                        if (priceDetails.length) {
                            for (const p of priceDetails) {
                                priceList.appendChild($el("div.sv-mp-price-row", {}, [
                                    $el("span.sv-mp-price-name", { textContent: p.name }),
                                    $el("span.sv-mp-price-val",  { textContent: `${p.price}/${p.unit}` }),
                                ]));
                            }
                        } else {
                            priceList.appendChild($el("span.sv-mp-price-empty", { textContent: "暂无价格" }));
                        }

                        gridEl.appendChild($el("div.sv-mp-card", {}, [
                            $el("div.sv-mp-card-head", {}, [
                                $el("div", {}, [
                                    $el("div.sv-mp-name", { textContent: displayName }),
                                    $el("div.sv-mp-tags-cell", { textContent: tags.length ? tags.join("、") : "未分类" }),
                                ]),
                                $el("span", {
                                    textContent: model.status === 1 ? "启用" : "停用",
                                    className: model.status === 1 ? "sv-mp-status-on" : "sv-mp-status-off",
                                }),
                            ]),
                            priceList,
                        ]));
                    }
                    contentDiv.replaceChildren(gridEl);
                    contentDiv.scrollTop = 0;
                }

                pageInfo.textContent = `第 ${currentPage} / ${totalPages} 页，共 ${total} 条`;
                prevBtn.disabled = currentPage <= 1;
                nextBtn.disabled = currentPage >= totalPages;
            } else {
                contentDiv.replaceChildren($el("div.sv-mp-empty", { textContent: data.message || "获取数据失败" }));
            }
        } catch (err) {
            contentDiv.replaceChildren($el("div.sv-mp-empty", { textContent: `加载失败: ${err.message}` }));
        }
    }
}
