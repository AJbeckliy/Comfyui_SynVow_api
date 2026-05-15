/**
 * SynVow 消费记录对话框
 */
import { $el, getToken, injectStyle, API_BASE } from "./dom.js";
import { showLoginDialog } from "./synvow_login.js";

let recordsDialog = null;
let currentPage = 1;

function extractUrls(value) {
    if (!value) return [];
    if (typeof value === "string") {
        if (/^https?:\/\//i.test(value)) return [value];
        try { return extractUrls(JSON.parse(value)); } catch { return []; }
    }
    if (Array.isArray(value)) return value.flatMap(extractUrls);
    if (typeof value === "object") {
        const urls = [];
        if (typeof value.url === "string" && /^https?:\/\//i.test(value.url)) urls.push(value.url);
        if (typeof value.result_file === "string" && /^https?:\/\//i.test(value.result_file)) urls.push(value.result_file);
        for (const key of ["data", "result", "results", "output", "sourceData", "task_result", "images", "videos", "audios"]) {
            urls.push(...extractUrls(value[key]));
        }
        return [...new Set(urls)];
    }
    return [];
}

export function showConsumptionRecordsDialog() {
    if (recordsDialog) { recordsDialog.remove(); recordsDialog = null; }
    currentPage = 1;

    injectStyle("sv-consumption-style", `
        .sv-cr-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-cr-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:680px; max-height:80vh; position:relative; display:flex; flex-direction:column; }
        .sv-cr-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-cr-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-cr-close:hover { color:white; }
        .sv-cr-content { flex:1; overflow-y:auto; margin-bottom:16px; }
        .sv-cr-table { width:100%; border-collapse:collapse; }
        .sv-cr-table th { background:#1e3a4a; color:#8899aa; font-size:12px; font-weight:normal; padding:12px 8px; text-align:left; }
        .sv-cr-table td { color:white; font-size:13px; padding:10px 8px; border-bottom:1px solid #334455; vertical-align:middle; }
        .sv-cr-table tr:hover td { background:#1e3a4a; }
        .sv-cr-table.loading { opacity:0.45; pointer-events:none; transition:opacity .15s; }
        .sv-cr-badge { padding:3px 8px; border-radius:4px; font-size:12px; }
        .sv-cr-success { background:#22c55e20; color:#22c55e; }
        .sv-cr-fail    { background:#ef444420; color:#ef4444; }
        .sv-cr-empty { text-align:center; color:#667788; padding:40px; }
        .sv-cr-link { color:#2dd4bf; font-size:12px; padding:3px 8px; border:1px solid #2dd4bf40; border-radius:4px; cursor:pointer; background:none; text-decoration:none; }
        .sv-cr-link:hover { background:#2dd4bf20; }
        .sv-cr-none { color:#445566; font-size:12px; }
        .sv-cr-pagination { display:flex; justify-content:center; align-items:center; gap:12px; }
        .sv-cr-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-cr-page-btn:hover { border-color:#2dd4bf; }
        .sv-cr-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-cr-page-info { color:#8899aa; font-size:13px; }
        .sv-cr-preview-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.85); display:flex; justify-content:center; align-items:center; z-index:10010; }
        .sv-cr-preview-box { position:relative; max-width:90vw; max-height:90vh; display:flex; align-items:center; justify-content:center; }
        .sv-cr-preview-close { position:absolute; top:-36px; right:0; background:none; border:none; color:white; font-size:28px; cursor:pointer; }
        .sv-cr-preview-media { max-width:85vw; max-height:85vh; border-radius:8px; }
        .sv-cr-preview-nav { position:absolute; top:50%; transform:translateY(-50%); background:rgba(0,0,0,0.5); border:none; color:white; font-size:36px; cursor:pointer; border-radius:4px; padding:4px 10px; }
        .sv-cr-preview-prev { left:-48px; }
        .sv-cr-preview-next { right:-48px; }
        .sv-cr-preview-count { position:absolute; bottom:-28px; left:50%; transform:translateX(-50%); color:#8899aa; font-size:13px; }
    `);

    const contentDiv = $el("div.sv-cr-content", {}, [
        $el("div.sv-cr-empty", { textContent: "加载中..." })
    ]);
    const prevBtn  = $el("button.sv-cr-page-btn", { textContent: "上一页", onclick: () => loadPage(currentPage - 1) });
    const nextBtn  = $el("button.sv-cr-page-btn", { textContent: "下一页", onclick: () => loadPage(currentPage + 1) });
    const pageInfo = $el("span.sv-cr-page-info");

    recordsDialog = $el("div.sv-cr-overlay", {
        onclick: (e) => { if (e.target === recordsDialog) hideConsumptionDialog(); }
    }, [
        $el("div.sv-cr-dialog", {}, [
            $el("button.sv-cr-close", { textContent: "×", onclick: hideConsumptionDialog }),
            $el("div.sv-cr-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> 消费记录` }),
            contentDiv,
            $el("div.sv-cr-pagination", {}, [prevBtn, pageInfo, nextBtn])
        ])
    ]);

    document.body.appendChild(recordsDialog);
    loadPage(1);

    let previewUrls = [], previewIdx = 0, previewEl = null;

    function openPreview(urls, idx = 0) {
        if (previewEl) previewEl.remove();
        previewUrls = urls; previewIdx = idx;
        previewEl = $el("div.sv-cr-preview-overlay", {
            onclick: (e) => { if (e.target === previewEl) closePreview(); }
        });
        renderPreview();
        document.body.appendChild(previewEl);
    }
    function closePreview() { if (previewEl) { previewEl.remove(); previewEl = null; } }
    function renderPreview() {
        if (!previewEl) return;
        previewEl.innerHTML = "";
        const url = previewUrls[previewIdx];
        const ext = url.split("?")[0].split(".").pop().toLowerCase();
        let media;
        if (["png","jpg","jpeg","webp","gif","bmp","svg"].includes(ext)) {
            media = $el("img.sv-cr-preview-media", { src: url });
        } else if (["mp4","webm","mov","avi","mkv"].includes(ext)) {
            media = $el("video.sv-cr-preview-media", { src: url, controls: true, autoplay: true });
        } else if (["mp3","wav","ogg","flac","aac","m4a"].includes(ext)) {
            media = $el("audio", { src: url, controls: true, autoplay: true });
        } else {
            media = Object.assign(document.createElement("a"), { href: url, target: "_blank", textContent: url, style: "color:#2dd4bf;word-break:break-all;" });
        }
        const box = $el("div.sv-cr-preview-box", {}, [
            $el("button.sv-cr-preview-close", { textContent: "×", onclick: closePreview }),
            media,
        ]);
        if (previewUrls.length > 1) {
            box.appendChild($el("button.sv-cr-preview-nav.sv-cr-preview-prev", { textContent: "‹", onclick: (e) => { e.stopPropagation(); previewIdx = (previewIdx - 1 + previewUrls.length) % previewUrls.length; renderPreview(); } }));
            box.appendChild($el("button.sv-cr-preview-nav.sv-cr-preview-next", { textContent: "›", onclick: (e) => { e.stopPropagation(); previewIdx = (previewIdx + 1) % previewUrls.length; renderPreview(); } }));
            box.appendChild($el("div.sv-cr-preview-count", { textContent: `${previewIdx + 1}/${previewUrls.length}` }));
        }
        previewEl.appendChild(box);
    }

    async function loadPage(page) {
        page = Math.max(1, parseInt(page) || 1);
        const token = getToken();
        if (!token) { showLoginDialog(); return; }

        const isFirst = !contentDiv.querySelector("table");
        if (!isFirst) {
            const tbl = contentDiv.querySelector("table");
            if (tbl) tbl.classList.add("loading");
        }
        prevBtn.disabled = true;
        nextBtn.disabled = true;

        try {
            const res  = await fetch(`${API_BASE}/account/consumption-records?page=${page}&per_page=10`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.code === 200 && data.data) {
                const d           = data.data;
                const items       = d.list || [];
                const total       = d.total || 0;
                const totalPages  = d.total_pages ?? (Math.ceil(total / 10) || 1);
                currentPage       = d.page ?? page;

                if (items.length === 0) {
                    contentDiv.innerHTML = '<div class="sv-cr-empty">暂无消费记录</div>';
                } else {
                    const tbody = $el("tbody");
                    for (const item of items) {
                        const ok  = item.status === 1;
                        const urls = ok ? extractUrls(item.source) : [];
                        const resCell = urls.length
                            ? $el("a.sv-cr-link", { textContent: "打开", href: "#", onclick: (e) => { e.preventDefault(); openPreview(urls); } })
                            : $el("span.sv-cr-none", { textContent: "无" });
                        tbody.appendChild($el("tr", {}, [
                            $el("td", { textContent: new Date(item.created_at).toLocaleString("zh-CN") }),
                            $el("td", { textContent: item.model_name || "-" }),
                            $el("td", {}, [$el("span.sv-cr-badge", { textContent: ok ? "成功" : "失败", className: `sv-cr-badge ${ok ? "sv-cr-success" : "sv-cr-fail"}` })]),
                            $el("td", { textContent: `${ok ? "-" : "+"}¥${parseFloat(item.amount || 0).toFixed(6)}`, style: { color: ok ? "#ef4444" : "#22c55e" } }),
                            $el("td", {}, [resCell]),
                        ]));
                    }
                    const table = $el("table.sv-cr-table", {}, [
                        $el("thead", {}, [$el("tr", {}, [
                            $el("th", { textContent: "时间" }),
                            $el("th", { textContent: "模型" }),
                            $el("th", { textContent: "状态" }),
                            $el("th", { textContent: "消费金额" }),
                            $el("th", { textContent: "资源(2h)" }),
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
                contentDiv.innerHTML = `<div class="sv-cr-empty">${data.message || "获取记录失败"}</div>`;
            }
        } catch {
            contentDiv.innerHTML = '<div class="sv-cr-empty">网络错误，请稍后重试</div>';
        }
    }
}

export function hideConsumptionDialog() {
    if (recordsDialog) recordsDialog.style.display = "none";
}
