/**
 * SynVow 充值记录对话框
 */
import { $el } from "./dom.js";

let recordsDialog = null;
let currentPage = 1;
const API_BASE = "/sv_api";

const STATUS_MAP = {
    1: { text: "待支付", color: "#f59e0b" },
    2: { text: "已支付", color: "#22c55e" },
    3: { text: "已过期", color: "#6b7280" },
    4: { text: "已取消", color: "#ef4444" }
};

const PAYMENT_MAP = {
    wechat: "微信支付",
    wxpay: "微信支付",
    alipay: "支付宝"
};

export function showRechargeRecordsDialog() {
    if (recordsDialog) {
        recordsDialog.remove();
        recordsDialog = null;
    }
    currentPage = 1;

    const style = document.createElement('style');
    style.textContent = `
        .sv-records-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-records-dialog { background:linear-gradient(180deg,#1a2a3a,#0d1a24); border-radius:12px; padding:30px; width:600px; max-height:80vh; position:relative; display:flex; flex-direction:column; }
        .sv-records-title { color:#2dd4bf; font-size:18px; font-weight:bold; margin-bottom:20px; display:flex; align-items:center; gap:8px; }
        .sv-records-close { position:absolute; top:16px; right:16px; background:none; border:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-records-close:hover { color:white; }
        .sv-records-table { width:100%; border-collapse:collapse; }
        .sv-records-table th { background:#1e3a4a; color:#8899aa; font-size:12px; font-weight:normal; padding:12px 8px; text-align:left; }
        .sv-records-table td { color:white; font-size:13px; padding:12px 8px; border-bottom:1px solid #334455; }
        .sv-records-table tr:hover td { background:#1e3a4a; }
        .sv-records-status { padding:4px 8px; border-radius:4px; font-size:12px; }
        .sv-records-empty { text-align:center; color:#667788; padding:40px; }
        .sv-records-loading { text-align:center; color:#667788; padding:40px; }
        .sv-records-content { flex:1; overflow-y:auto; margin-bottom:16px; }
        .sv-records-pagination { display:flex; justify-content:center; align-items:center; gap:12px; }
        .sv-records-page-btn { background:#1e3a4a; border:1px solid #334455; border-radius:4px; padding:6px 12px; color:white; font-size:13px; cursor:pointer; }
        .sv-records-page-btn:hover { border-color:#2dd4bf; }
        .sv-records-page-btn:disabled { opacity:0.5; cursor:not-allowed; }
        .sv-records-page-info { color:#8899aa; font-size:13px; }
    `;
    document.head.appendChild(style);

    const contentDiv = $el("div.sv-records-content", {}, [
        $el("div.sv-records-loading", { textContent: "加载中..." })
    ]);

    const prevBtn = $el("button.sv-records-page-btn", { textContent: "上一页", onclick: () => loadPage(currentPage - 1) });
    const nextBtn = $el("button.sv-records-page-btn", { textContent: "下一页", onclick: () => loadPage(currentPage + 1) });
    const pageInfo = $el("span.sv-records-page-info", { textContent: "第 1 页" });

    const pagination = $el("div.sv-records-pagination", {}, [prevBtn, pageInfo, nextBtn]);

    recordsDialog = $el("div.sv-records-overlay", {
        onclick: (e) => { if (e.target === recordsDialog) hideRecordsDialog(); }
    }, [
        $el("div.sv-records-dialog", {}, [
            $el("button.sv-records-close", { textContent: "×", onclick: hideRecordsDialog }),
            $el("div.sv-records-title", { innerHTML: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg> 充值记录` }),
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
            contentDiv.innerHTML = '<div class="sv-records-empty">请先登录</div>';
            return;
        }

        contentDiv.innerHTML = '<div class="sv-records-loading">加载中...</div>';
        prevBtn.disabled = true;
        nextBtn.disabled = true;

        try {
            const url = `${API_BASE}/account/recharge-records?page=${page}&per_page=10`;
            console.log("[SynVow 充值记录] 请求: https://service.synvow.com/api/v1/account/recharge-records?page=" + page + "&per_page=10");
            const res = await fetch(url, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            const data = await res.json();
            console.log("[SynVow 充值记录] 响应:", JSON.stringify(data, null, 2));

            if (data.code === 200 && data.data) {
                const items = data.data.items || data.data.list || [];
                const total = data.data.total || 0;
                const total_pages = data.data.total_pages || data.data.totalPages || Math.ceil(total / 10) || 1;
                const current_page = data.data.current_page || data.data.currentPage || page;
                currentPage = current_page;

                if (!items || items.length === 0) {
                    contentDiv.innerHTML = '<div class="sv-records-empty">暂无充值记录</div>';
                } else {
                    contentDiv.innerHTML = `
                        <table class="sv-records-table">
                            <thead>
                                <tr>
                                    <th>订单号</th>
                                    <th>金额</th>
                                    <th>支付方式</th>
                                    <th>状态</th>
                                    <th>时间</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${items.map(item => {
                                    const status = STATUS_MAP[item.status] || { text: "未知", color: "#6b7280" };
                                    const payment = PAYMENT_MAP[item.payment_type] || item.payment_type;
                                    const time = new Date(item.created_at).toLocaleString('zh-CN');
                                    return `
                                        <tr>
                                            <td>${item.order_no}</td>
                                            <td>¥${parseFloat(item.amount).toFixed(2)}</td>
                                            <td>${payment}</td>
                                            <td><span class="sv-records-status" style="background:${status.color}20;color:${status.color}">${status.text}</span></td>
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
                contentDiv.innerHTML = `<div class="sv-records-empty">${data.message || '获取记录失败'}</div>`;
            }
        } catch (e) {
            contentDiv.innerHTML = '<div class="sv-records-empty">网络错误，请稍后重试</div>';
        }
    }
}

export function hideRecordsDialog() {
    if (recordsDialog) recordsDialog.style.display = "none";
}
