/**
 * 模型价格对话框
 */
import { $el, injectStyle, API_BASE, paginationCss } from "./dom.js";

let priceDialog = null;
let currentPage = 1;

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

export function showModelPriceDialog(modelId = "") {
    if (priceDialog) { priceDialog.remove(); priceDialog = null; }
    currentPage = 1;

    injectStyle("sv-price-style", `
        .sv-mp-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-mp-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:14px; padding:28px; width:920px; max-height:82vh; position:relative; display:flex; flex-direction:column; box-shadow:0 24px 80px rgba(0,0,0,.45); border:1px solid rgba(45,212,191,.16); }
        .sv-mp-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-mp-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-mp-close:hover { color:white; }
        .sv-mp-content { flex:1; overflow-y:auto; margin-bottom:16px; }
        .sv-mp-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
        .sv-mp-grid.loading { opacity:0.45; pointer-events:none; transition:opacity .15s; }
        .sv-mp-card { background:rgba(16,41,56,.55); border:1px solid rgba(80,105,125,.35); border-radius:10px; padding:14px 16px; display:flex; flex-direction:column; gap:10px; }
        .sv-mp-card-head { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; }
        .sv-mp-name { color:#fff; font-weight:700; font-size:14px; line-height:1.35; }
        .sv-mp-tags-cell { color:#8899aa; font-size:12px; margin-top:4px; }
        .sv-mp-price-list { display:flex; flex-direction:column; gap:4px; }
        .sv-mp-price-row { display:flex; align-items:center; justify-content:space-between; gap:6px; background:rgba(45,212,191,.05); border-radius:6px; padding:5px 9px; line-height:1.6; }
        .sv-mp-price-name { color:#9aabba; font-size:12px; }
        .sv-mp-price-val { color:#2dd4bf; font-weight:700; font-size:13px; white-space:nowrap; }
        .sv-mp-price-empty { color:#667788; font-size:12px; }
        .sv-mp-status-on  { color:#22c55e; font-size:12px; flex-shrink:0; }
        .sv-mp-status-off { color:#ef4444; font-size:12px; flex-shrink:0; }
        .sv-mp-empty { text-align:center; color:#667788; padding:40px; }
    ` + paginationCss("sv-mp"));

    const contentDiv = $el("div.sv-mp-content", {}, [
        $el("div.sv-mp-empty", { textContent: "加载中..." })
    ]);
    const prevBtn  = $el("button.sv-mp-page-btn", { textContent: "上一页", onclick: () => loadPage(currentPage - 1) });
    const nextBtn  = $el("button.sv-mp-page-btn", { textContent: "下一页", onclick: () => loadPage(currentPage + 1) });
    const pageInfo = $el("span.sv-mp-page-info");

    priceDialog = $el("div.sv-mp-overlay", {
        onclick: (e) => { if (e.target === priceDialog) priceDialog.remove(); }
    }, [
        $el("div.sv-mp-dialog", {}, [
            $el("button.sv-mp-close", { textContent: "×", onclick: () => priceDialog.remove() }),
            $el("div.sv-mp-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg> 模型价格` }),
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
            const pageSize = 21;
            const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort_by: "sort", sort_order: "ASC" });
            if (modelId) params.set("model_id", modelId);
            const res  = await fetch(`${API_BASE}/models/public-list?${params.toString()}`);
            const text = await res.text();
            if (!text) throw new Error(`接口无响应(${res.status})`);
            const data = JSON.parse(text);
            if (data.code === 200 && data.data) {
                const { items, total, totalPages, page: normalizedPage } = normalizeModelListPayload(data, page, pageSize);
                currentPage = normalizedPage;

                if (items.length === 0) {
                    contentDiv.innerHTML = '<div class="sv-mp-empty">暂无价格数据</div>';
                } else {
                    const gridEl = $el("div.sv-mp-grid");
                    for (const model of items) {
                        const displayName = model.name || "-";
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
                    contentDiv.innerHTML = "";
                    contentDiv.appendChild(gridEl);
                }

                pageInfo.textContent = `第 ${currentPage} / ${totalPages} 页，共 ${total} 条`;
                prevBtn.disabled = currentPage <= 1;
                nextBtn.disabled = currentPage >= totalPages;
            } else {
                contentDiv.innerHTML = `<div class="sv-mp-empty">${data.message || "获取数据失败"}</div>`;
            }
        } catch (err) {
            contentDiv.innerHTML = `<div class="sv-mp-empty">加载失败: ${err.message}</div>`;
        }
    }
}
