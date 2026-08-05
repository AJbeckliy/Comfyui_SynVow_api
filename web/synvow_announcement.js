/**
 * SynVow 公告列表与详情。
 */
import { $el, authedGet, getToken, injectStyle, paginationCss } from "./dom.js";

const READ_KEY = "synvow_announcement_read_id";
const CATEGORY_ID = 2;
const PAGE_SIZE = 10;
let dialog = null;
let latestId = 0;

function listPath(page, perPage = PAGE_SIZE) {
    return `/content/announcements?page=${page}&per_page=${perPage}&category_id=${CATEGORY_ID}`;
}

async function fetchAnnouncement(path) {
    const data = await authedGet(path, getToken());
    console.log("[SynVow 公告] 请求返回:", { path, data });
    return data;
}

function ensureDialogStyle() {
    injectStyle("sv-announcement-style", `
        .sv-an-overlay { position:fixed; inset:0; background:rgba(0,0,0,.7); display:flex; justify-content:center; align-items:center; z-index:10001; }
        .sv-an-dialog { width:min(760px,90vw); max-height:82vh; padding:24px; box-sizing:border-box; display:flex; flex-direction:column; position:relative; border-radius:14px; background:linear-gradient(180deg,#1a2a3a,#0d1a24); border:1px solid rgba(45,212,191,.16); box-shadow:0 24px 80px rgba(0,0,0,.45); color:white; }
        .sv-an-title { color:#2dd4bf; font-size:19px; font-weight:700; margin-bottom:16px; }
        .sv-an-close { position:absolute; top:12px; right:14px; border:none; background:none; color:#667788; font-size:24px; cursor:pointer; }
        .sv-an-close:hover { color:white; }
        .sv-an-content { min-height:180px; overflow:auto; margin-bottom:14px; }
        .sv-an-item { padding:13px 14px; border:1px solid #263b4b; border-radius:8px; margin-bottom:9px; background:rgba(16,41,56,.55); cursor:pointer; }
        .sv-an-item:hover { border-color:#2dd4bf; }
        .sv-an-item-head { display:flex; justify-content:space-between; gap:12px; align-items:center; }
        .sv-an-item-title { color:#fff; font-size:14px; font-weight:700; }
        .sv-an-item-date { color:#71869a; font-size:12px; white-space:nowrap; }
        .sv-an-item-summary { color:#9aabba; font-size:13px; line-height:1.5; margin-top:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .sv-an-latest { color:#2dd4bf; font-size:11px; border:1px solid #2dd4bf; border-radius:10px; padding:1px 6px; margin-left:7px; }
        .sv-an-empty { color:#71869a; text-align:center; padding:60px 20px; }
        .sv-an-back { border:none; background:none; color:#2dd4bf; cursor:pointer; padding:0; margin-bottom:12px; font-size:13px; text-align:left; }
        .sv-an-detail-title { font-size:20px; font-weight:700; margin-bottom:7px; }
        .sv-an-detail-date { color:#71869a; font-size:12px; margin-bottom:14px; }
        .sv-an-detail-cover { display:block; max-width:100%; max-height:280px; margin:0 auto 16px; border-radius:8px; }
        .sv-an-detail-body { color:#d7e0e8; font-size:14px; line-height:1.7; overflow-wrap:anywhere; }
        .sv-an-detail-body img { max-width:100%; height:auto; }
    ` + paginationCss("sv-an"));
}

function setUnread(button, unread) {
    const dot = button.querySelector(".sv-announcement-dot");
    if (unread && !dot) button.appendChild($el("span.sv-announcement-dot"));
    if (!unread && dot) dot.remove();
}

function markRead(button) {
    if (latestId > 0) localStorage.setItem(READ_KEY, String(latestId));
    setUnread(button, false);
}

function showMessage(container, message) {
    container.replaceChildren($el("div.sv-an-empty", { textContent: message }));
}

export async function checkAnnouncementUnread(button) {
    try {
        const data = await fetchAnnouncement(listPath(1, 1));
        if (data?.code !== 200) return;
        latestId = Number(data.data?.list?.[0]?.id ?? 0) || 0;
        setUnread(button, latestId > (Number(localStorage.getItem(READ_KEY) ?? 0) || 0));
    } catch (_) {}
}

export function showAnnouncementDialog(button) {
    if (dialog) dialog.remove();
    ensureDialogStyle();

    let currentPage = 1;
    let totalPages = 1;
    const content = $el("div.sv-an-content");
    const prev = $el("button.sv-an-page-btn", { textContent: "上一页" });
    const next = $el("button.sv-an-page-btn", { textContent: "下一页" });
    const pageInfo = $el("span.sv-an-page-info");
    const pagination = $el("div.sv-an-pagination", {}, [prev, pageInfo, next]);

    dialog = $el("div.sv-an-overlay", {
        onclick: (event) => { if (event.target === dialog) dialog.remove(); },
    }, [
        $el("div.sv-an-dialog", {}, [
            $el("button.sv-an-close", { textContent: "×", onclick: () => dialog.remove() }),
            $el("div.sv-an-title", { textContent: "公告" }),
            content,
            pagination,
        ]),
    ]);
    document.body.appendChild(dialog);

    const loadDetail = async (id) => {
        showMessage(content, "加载中...");
        try {
            const data = await fetchAnnouncement(`/content/announcements/${id}`);
            if (data?.code !== 200 || !data.data) throw new Error(data?.message || "加载失败");
            const item = data.data;
            content.replaceChildren(
                $el("button.sv-an-back", { textContent: "← 返回公告列表", onclick: () => loadPage(currentPage) }),
                $el("div.sv-an-detail-title", { textContent: item.title || "" }),
                $el("div.sv-an-detail-date", { textContent: item.created_at?.slice(0, 10) || "" }),
                ...(item.cover_image ? [$el("img.sv-an-detail-cover", { src: item.cover_image, alt: "" })] : []),
                $el("div.sv-an-detail-body", { innerHTML: item.content || "" }),
            );
            pagination.style.display = "none";
        } catch (error) {
            showMessage(content, error.message || "加载失败");
        }
    };

    const loadPage = async (page) => {
        showMessage(content, "加载中...");
        pagination.style.display = "flex";
        prev.disabled = true;
        next.disabled = true;
        try {
            const data = await fetchAnnouncement(listPath(page));
            if (data?.code !== 200) throw new Error(data?.message || "加载失败");
            const items = data.data?.list ?? [];
            const total = Number(data.data?.total ?? items.length);
            currentPage = Number(data.data?.page ?? page);
            totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
            content.replaceChildren();
            if (!items.length) {
                content.appendChild($el("div.sv-an-empty", { textContent: "暂无公告" }));
            } else {
                items.forEach((item, index) => {
                    const title = $el("span.sv-an-item-title", { textContent: item.title || "未命名公告" });
                    if (currentPage === 1 && index === 0) {
                        title.appendChild($el("span.sv-an-latest", { textContent: "最新" }));
                    }
                    content.appendChild($el("div.sv-an-item", { onclick: () => loadDetail(item.id) }, [
                        $el("div.sv-an-item-head", {}, [
                            title,
                            $el("span.sv-an-item-date", { textContent: item.created_at?.slice(0, 10) || "" }),
                        ]),
                        $el("div.sv-an-item-summary", { textContent: item.summary || "" }),
                    ]));
                });
            }
            if (currentPage === 1) {
                const firstId = Number(items[0]?.id ?? 0) || 0;
                if (firstId > latestId) latestId = firstId;
                markRead(button);
            }
            pageInfo.textContent = `${currentPage} / ${totalPages}`;
            prev.disabled = currentPage <= 1;
            next.disabled = currentPage >= totalPages;
        } catch (error) {
            showMessage(content, error.message || "加载失败");
        }
    };

    prev.onclick = () => loadPage(currentPage - 1);
    next.onclick = () => loadPage(currentPage + 1);
    loadPage(1);
}
