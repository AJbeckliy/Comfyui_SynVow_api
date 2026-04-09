/**
 * 模型价格对话框
 */
import { $el } from "./dom.js";

export function showModelPriceDialog() {
    const token = localStorage.getItem("sv_token");
    if (!token || token === "undefined" || token === "") {
        alert("请先登录后查看模型价格");
        const loginEvent = new Event('click');
        document.getElementById('sv-user-btn')?.dispatchEvent(loginEvent);
        return;
    }

    const existing = document.querySelector(".sv-price-overlay");
    if (existing) existing.remove();

    const style = document.createElement('style');
    style.textContent = `
        .sv-price-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-price-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:90%; max-width:900px; height:60vh; display:flex; flex-direction:column; position:relative; overflow:hidden; }
        .sv-price-content { flex:1; overflow:hidden; margin-bottom:20px; margin-top:20px; }
        .sv-price-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-price-title svg { width:18px; height:18px; }
        .sv-price-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:20px; cursor:pointer; line-height:1; }
        .sv-price-close:hover { color:white; }
        .sv-price-tabs { display:flex; gap:12px; margin-bottom:20px; }
        .sv-price-tab { background:#1e3a4a; border:2px solid #334455; border-radius:8px; padding:10px 20px; color:white; font-size:14px; cursor:pointer; }
        .sv-price-tab:hover { border-color:#2dd4bf; }
        .sv-price-tab.active { border-color:#2dd4bf; background:#1e4a5a; }
        .sv-price-table { width:100%; border-collapse:collapse; color:white; font-size:13px; table-layout:fixed; }
        .sv-price-table th { background:#1e3a4a; color:#8899aa; font-size:12px; font-weight:normal; padding:12px 8px; text-align:left; border-bottom:2px solid #334455; }
        .sv-price-table th:nth-child(1) { width:20%; }
        .sv-price-table th:nth-child(2) { width:40%; }
        .sv-price-table th:nth-child(3) { width:25%; }
        .sv-price-table th:nth-child(4) { width:15%; }
        .sv-price-table td { color:white; font-size:13px; padding:12px 8px; border-bottom:1px solid #334455; text-align:left; vertical-align:middle; word-wrap:break-word; }
        .sv-price-table tr:hover td { background:#1e3a4a; }
        .sv-price-pagination { display:flex; justify-content:center; align-items:center; gap:10px; margin-top:20px; }
        .sv-price-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-price-page-btn:hover { border-color:#2dd4bf; }
        .sv-price-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-price-page-info { color:#8899aa; font-size:13px; }
        .sv-price-loading { color:#667788; text-align:center; padding:40px; }
        .sv-price-error { color:#ff6b6b; text-align:center; padding:20px; }
        .sv-price-empty { color:#667788; text-align:center; padding:20px; }
        .sv-price-desc { font-size:12px; color:#aaa; max-width:300px; line-height:1.5; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
        .sv-price-detail { line-height:1.5; font-size:13px; }
    `;
    document.head.appendChild(style);

    const priceIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>';
    const loading = $el("div.sv-price-loading", { textContent: "加载中..." });
    const tabsContainer = $el("div.sv-price-tabs");
    const contentContainer = $el("div.sv-price-content", {}, [loading]);

    const overlay = $el("div.sv-price-overlay", {
        onclick: function(e) { if (e.target === overlay) overlay.remove(); }
    }, [
        $el("div.sv-price-dialog", {}, [
            $el("button.sv-price-close", { textContent: "×", onclick: function() { overlay.remove(); } }),
            $el("div.sv-price-title", { innerHTML: priceIcon + " 模型价格" }),
            tabsContainer,
            contentContainer
        ])
    ]);

    document.body.appendChild(overlay);
    fetchModelPrices(contentContainer, tabsContainer);
}

async function fetchModelPrices(container, tabsContainer) {
    try {
        const token = localStorage.getItem("sv_token");
        const headers = { "Authorization": "Bearer " + token };

        var list = [];
        var page = 1;
        while (true) {
            const res = await fetch("/sv_api/models?page=" + page + "&per_page=50", { headers: headers });
            if (!res.ok) throw new Error("HTTP " + res.status);
            const data = await res.json();
            var pageList = [];
            if (data.code === 200 && data.data && Array.isArray(data.data.list)) {
                pageList = data.data.list;
                var total = data.data.total || 0;
                list = list.concat(pageList);
                if (list.length >= total || pageList.length === 0) break;
            } else if (data.code === 200 && Array.isArray(data.data)) {
                list = list.concat(data.data);
                break;
            } else if (Array.isArray(data)) {
                list = list.concat(data);
                break;
            } else {
                container.innerHTML = '<div class="sv-price-error">数据格式错误</div>';
                return;
            }
            page++;
        }
        container.innerHTML = "";

        if (list.length === 0) {
            container.innerHTML = '<div class="sv-price-empty">暂无价格数据</div>';
            return;
        }

        var categoryMap = { "视频": "视频", "文本对话": "语言", "推理": "语言", "多模态": "语言", "图形生成": "图像", "图像": "图像", "音频": "音频" };
        var categories = ["语言", "视频", "图像"];
        var categorizedData = { "语言": [], "视频": [], "图像": [], "音频": [] };

        list = list.filter(function(item) { return item.status === 1; });

        list.forEach(function(item) {
            var tags = item.tags || [];
            tags.forEach(function(tag) {
                var mappedCat = categoryMap[tag.name];
                if (mappedCat && categorizedData[mappedCat]) {
                    var exists = categorizedData[mappedCat].find(function(i) { return i.id === item.id; });
                    if (!exists) categorizedData[mappedCat].push(item);
                }
            });
        });

        var currentCategory = categories[0];

        tabsContainer.innerHTML = "";
        categories.forEach(function(cat) {
            var count = categorizedData[cat].length;
            var tab = $el("button.sv-price-tab", {
                textContent: cat + " (" + count + ")",
                className: cat === currentCategory ? "sv-price-tab active" : "sv-price-tab",
                onclick: function() {
                    currentCategory = cat;
                    var tabs = document.querySelectorAll(".sv-price-tab");
                    tabs.forEach(function(t) { t.classList.remove("active"); });
                    tab.classList.add("active");
                    renderCategory(categorizedData[cat]);
                }
            });
            tabsContainer.appendChild(tab);
        });

        function renderCategory(categoryList) {
            var pageSize = 5;
            var currentPage = 1;
            var totalPages = Math.ceil(categoryList.length / pageSize);

            function renderPage(page) {
                var start = (page - 1) * pageSize;
                var end = start + pageSize;
                var pageData = categoryList.slice(start, end);

                var table = $el("table.sv-price-table");
                var thead = $el("thead");
                var headerRow = $el("tr");
                ["模型名称", "描述", "价格", "单位"].forEach(function(text) {
                    headerRow.appendChild($el("th", { textContent: text }));
                });
                thead.appendChild(headerRow);
                table.appendChild(thead);

                var tbody = $el("tbody");
                pageData.forEach(function(item) {
                    var row = $el("tr");
                    row.appendChild($el("td", { textContent: item.name || "-" }));
                    row.appendChild($el("td", { innerHTML: '<div class="sv-price-desc">' + (item.description || "-") + '</div>' }));

                    var priceDetails = item.price_details || [];
                    var priceText = priceDetails.map(function(p) { return p.name + ": " + p.price; }).join(", ");
                    var priceHtml = priceText ? '<div class="sv-price-detail">' + priceText.replace(/,\s*/g, '<br>') + '</div>' : "-";
                    row.appendChild($el("td", { innerHTML: priceHtml }));

                    var unitText = priceDetails.map(function(p) {
                        var unit = p.unit || "";
                        return unit === "tokens" ? "k/tokens" : unit;
                    }).filter(function(v, i, a) { return a.indexOf(v) === i; }).join(", ") || "-";
                    row.appendChild($el("td", { textContent: unitText }));

                    tbody.appendChild(row);
                });
                table.appendChild(tbody);

                container.innerHTML = "";
                container.appendChild(table);

                if (totalPages > 1) {
                    var pagination = $el("div.sv-price-pagination");
                    var prevBtn = $el("button.sv-price-page-btn", {
                        textContent: "上一页",
                        disabled: page === 1,
                        onclick: function() { currentPage--; renderPage(currentPage); }
                    });
                    var pageInfo = $el("span.sv-price-page-info", { textContent: page + " / " + totalPages });
                    var nextBtn = $el("button.sv-price-page-btn", {
                        textContent: "下一页",
                        disabled: page === totalPages,
                        onclick: function() { currentPage++; renderPage(currentPage); }
                    });

                    pagination.appendChild(prevBtn);
                    pagination.appendChild(pageInfo);
                    pagination.appendChild(nextBtn);
                    container.appendChild(pagination);
                }
            }

            renderPage(currentPage);
        }

        renderCategory(categorizedData[currentCategory]);

    } catch (err) {
        container.innerHTML = '<div class="sv-price-error">加载失败: ' + err.message + '</div>';
    }
}
