/**
 * SynVow 消费记录对话框
 */
import { $el } from "./dom.js";

let recordsDialog = null;
let currentPage = 1;
const API_BASE = "/sv_api";

const STATUS_MAP = { 1: "成功" };

export function showConsumptionRecordsDialog() {
    if (recordsDialog) {
        recordsDialog.remove();
        recordsDialog = null;
    }
    currentPage = 1;

    const style = document.createElement('style');
    style.textContent = `
        .sv-consumption-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-consumption-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:650px; max-height:80vh; position:relative; display:flex; flex-direction:column; }
        .sv-consumption-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-consumption-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-consumption-close:hover { color:white; }
        .sv-consumption-table { width:100%; border-collapse:collapse; }
        .sv-consumption-table th { background:#1e3a4a; color:#8899aa; font-size:12px; font-weight:normal; padding:12px 8px; text-align:left; }
        .sv-consumption-table td { color:white; font-size:13px; padding:12px 8px; border-bottom:1px solid #334455; }
        .sv-consumption-table tr:hover td { background:#1e3a4a; }
        .sv-consumption-type { padding:4px 8px; border-radius:4px; font-size:12px; background:#3b82f620; color:#3b82f6; }
        .sv-consumption-empty { text-align:center; color:#667788; padding:40px; }
        .sv-consumption-loading { text-align:center; color:#667788; padding:40px; }
        .sv-consumption-content { flex:1; overflow-y:auto; margin-bottom:16px; }
        .sv-consumption-pagination { display:flex; justify-content:center; align-items:center; gap:12px; }
        .sv-consumption-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-consumption-page-btn:hover { border-color:#2dd4bf; }
        .sv-consumption-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-consumption-page-info { color:#8899aa; font-size:13px; }
        .sv-consumption-amount { color:#ef4444; }
    `;
    document.head.appendChild(style);

    const contentDiv = $el("div.sv-consumption-content", {}, [
        $el("div.sv-consumption-loading", { textContent: "加载中..." })
    ]);

    const prevBtn = $el("button.sv-consumption-page-btn", { textContent: "上一页", onclick: () => loadPage(currentPage - 1) });
    const nextBtn = $el("button.sv-consumption-page-btn", { textContent: "下一页", onclick: () => loadPage(currentPage + 1) });
    const pageInfo = $el("span.sv-consumption-page-info", { textContent: "第 1 页" });

    const pagination = $el("div.sv-consumption-pagination", {}, [prevBtn, pageInfo, nextBtn]);

    recordsDialog = $el("div.sv-consumption-overlay", {
        onclick: (e) => { if (e.target === recordsDialog) hideConsumptionDialog(); }
    }, [
        $el("div.sv-consumption-dialog", {}, [
            $el("button.sv-consumption-close", { textContent: "×", onclick: hideConsumptionDialog }),
            $el("div.sv-consumption-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> 消费记录` }),
            contentDiv,
            pagination
        ])
    ]);

    document.body.appendChild(recordsDialog);

    // 加载数据
    loadPage(1);

    async function loadPage(page) {
        page = parseInt(page) || 1;
        if (page < 1) page = 1;
        
        const token = localStorage.getItem("sv_token");
        if (!token) {
            contentDiv.innerHTML = '<div class="sv-consumption-empty">请先登录</div>';
            return;
        }

        contentDiv.innerHTML = '<div class="sv-consumption-loading">加载中...</div>';
        prevBtn.disabled = true;
        nextBtn.disabled = true;

        try {
            const url = `${API_BASE}/account/consumption-records?page=${page}&per_page=10`;
            console.log("[SynVow 消费记录] 请求: https://service.synvow.com/api/v1/account/consumption-records?page=" + page + "&per_page=10");
            const res = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            console.log("[SynVow 消费记录] 响应:", JSON.stringify(data, null, 2));

            if (data.code === 200 && data.data) {
                const items = data.data.items || data.data.list || [];
                const total = data.data.total || 0;
                const total_pages = data.data.total_pages || data.data.totalPages || Math.ceil(total / 10) || 1;
                const current_page = data.data.current_page || data.data.currentPage || page;
                currentPage = current_page;

                if (!items || items.length === 0) {
                    contentDiv.innerHTML = '<div class="sv-consumption-empty">暂无消费记录</div>';
                } else {
                    contentDiv.innerHTML = `
                        <table class="sv-consumption-table">
                            <thead>
                                <tr>
                                    <th>状态</th>
                                    <th>模型</th>
                                    <th>消费金额</th>
                                    <th>时间</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${items.map(item => {
                                    const modelName = item.model_name || item.type || '-';
                                    const statusOk = item.status === 1;
                                    const statusBadge = `<span class="sv-consumption-type" style="background:${statusOk ? '#22c55e20' : '#ef444420'};color:${statusOk ? '#22c55e' : '#ef4444'}">${statusOk ? '成功' : '失败'}</span>`;
                                    const time = new Date(item.created_at).toLocaleString('zh-CN');
                                    return `
                                        <tr>
                                            <td>${statusBadge}</td>
                                            <td>${modelName}</td>
                                            <td class="sv-consumption-amount" style="color:${statusOk ? '#ef4444' : '#22c55e'}">${statusOk ? '-' : '+'}¥${parseFloat(item.amount).toFixed(5)}</td>
                                            <td>${time}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    `;
                }

                pageInfo.textContent = `第 ${current_page} / ${total_pages} 页，共 ${total} 条`;
                prevBtn.disabled = current_page <= 1;
                nextBtn.disabled = current_page >= total_pages;
            } else {
                contentDiv.innerHTML = `<div class="sv-consumption-empty">${data.message || '获取记录失败'}</div>`;
            }
        } catch (e) {
            contentDiv.innerHTML = '<div class="sv-consumption-empty">网络错误，请稍后重试</div>';
        }
    }
}

export function hideConsumptionDialog() {
    if (recordsDialog) recordsDialog.style.display = "none";
}
