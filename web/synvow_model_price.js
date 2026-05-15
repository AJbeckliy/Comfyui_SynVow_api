/**
 * 模型价格对话框
 */
import { $el, getToken, injectStyle, API_BASE } from "./dom.js";

let priceDialog = null;
let currentPage = 1;

export function showModelPriceDialog() {
    if (priceDialog) { priceDialog.remove(); priceDialog = null; }
    currentPage = 1;

    injectStyle("sv-price-style", `
        .sv-mp-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-mp-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:760px; max-height:80vh; position:relative; display:flex; flex-direction:column; }
        .sv-mp-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-mp-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-mp-close:hover { color:white; }
        .sv-mp-content { flex:1; overflow-y:auto; margin-bottom:16px; }
        .sv-mp-table { width:100%; border-collapse:collapse; }
        .sv-mp-table th { background:#1e3a4a; color:#8899aa; font-size:12px; font-weight:normal; padding:12px 8px; text-align:left; }
        .sv-mp-table td { color:white; font-size:13px; padding:10px 8px; border-bottom:1px solid #334455; vertical-align:top; }
        .sv-mp-table tr:hover td { background:#1e3a4a; }
        .sv-mp-table.loading { opacity:0.45; pointer-events:none; transition:opacity .15s; }
        .sv-mp-price-row { display:flex; align-items:center; gap:6px; line-height:1.8; }
        .sv-mp-price-name { color:#8899aa; font-size:12px; }
        .sv-mp-price-sep { color:#445566; }
        .sv-mp-price-val { color:#2dd4bf; }
        .sv-mp-tags { color:#8899aa; font-size:12px; }
        .sv-mp-status-on  { color:#22c55e; }
        .sv-mp-status-off { color:#ef4444; }
        .sv-mp-empty { text-align:center; color:#667788; padding:40px; }
        .sv-mp-pagination { display:flex; justify-content:center; align-items:center; gap:12px; }
        .sv-mp-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-mp-page-btn:hover { border-color:#2dd4bf; }
        .sv-mp-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-mp-page-info { color:#8899aa; font-size:13px; }
    `);

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
            $el("div.sv-mp-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> 模型价格` }),
            contentDiv,
            $el("div.sv-mp-pagination", {}, [prevBtn, pageInfo, nextBtn])
        ])
    ]);

    document.body.appendChild(priceDialog);
    loadPage(1);

    async function loadPage(page) {
        page = Math.max(1, parseInt(page) || 1);

        const tbl = contentDiv.querySelector("table");
        if (tbl) tbl.classList.add("loading");
        prevBtn.disabled = true;
        nextBtn.disabled = true;

        try {
            const params = new URLSearchParams({ page: String(page), page_size: "20", sort_by: "sort", sort_order: "ASC" });
            const res  = await fetch(`${API_BASE}/models/public-list?${params.toString()}`);
            const text = await res.text();
            if (!text) throw new Error(`接口无响应(${res.status})`);
            const data = JSON.parse(text);
            if (data.code === 200 && data.data) {
                const d          = data.data;
                const items      = Array.isArray(d) ? d : (d.list ?? []);
                const total      = d.total ?? 0;
                const totalPages = d.total_pages ?? (Math.ceil(total / 20) || 1);
                currentPage      = d.page ?? page;

                if (items.length === 0) {
                    contentDiv.innerHTML = '<div class="sv-mp-empty">暂无价格数据</div>';
                } else {
                    const tbody = $el("tbody");
                    for (const model of items) {
                        const priceDetails = model.price_details || [];
                        const priceCell = $el("td");
                        if (priceDetails.length) {
                            for (const p of priceDetails) {
                                priceCell.appendChild($el("div.sv-mp-price-row", {}, [
                                    $el("span.sv-mp-price-name", { textContent: p.name }),
                                    $el("span.sv-mp-price-sep",  { textContent: "|" }),
                                    $el("span.sv-mp-price-val",  { textContent: `${p.price}/${p.unit}` }),
                                ]));
                            }
                        } else {
                            priceCell.textContent = "—";
                        }
                        const tags = (model.tags || []).map(t => t.name).join("、") || "—";
                        tbody.appendChild($el("tr", {}, [
                            $el("td", { textContent: model.name || "-" }),
                            priceCell,
                            $el("td.sv-mp-tags", { textContent: tags }),
                            $el("td", {}, [$el("span", {
                                textContent: model.status === 1 ? "启用" : "停用",
                                className: model.status === 1 ? "sv-mp-status-on" : "sv-mp-status-off"
                            })]),
                        ]));
                    }
                    const table = $el("table.sv-mp-table", {}, [
                        $el("thead", {}, [$el("tr", {}, [
                            $el("th", { textContent: "模型名称" }),
                            $el("th", { textContent: "价格" }),
                            $el("th", { textContent: "标签" }),
                            $el("th", { textContent: "状态" }),
                        ])]),
                        tbody
                    ]);
                    contentDiv.innerHTML = "";
                    contentDiv.appendChild(table);
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
