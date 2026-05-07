// ====================== HISTORY JS (FULL) ======================
"use strict";

// ── DOM refs ─────────────────────────────────────────────────────────────────
const logList      = document.getElementById("logList");
const loadMoreWrap = document.getElementById("loadMoreWrap");
const loadMoreBtn  = document.getElementById("loadMoreBtn");
const searchInput  = document.getElementById("searchInput");
const searchClear  = document.getElementById("searchClear");
const typeChips    = document.getElementById("typeChips");
const dateFrom     = document.getElementById("dateFrom");
const dateTo       = document.getElementById("dateTo");
const dateClear    = document.getElementById("dateClear");
const totalNum     = document.getElementById("totalNum");
const ssrPagination = document.getElementById("ssrPagination");

// Stats
const cntSale    = document.getElementById("cntSale");
const cntPayment = document.getElementById("cntPayment");
const cntReturn  = document.getElementById("cntReturn");
const cntStock   = document.getElementById("cntStock");

// Modal
const detailModal       = new bootstrap.Modal(document.getElementById("detailModal"));
const detailIcon        = document.getElementById("detailIcon");
const detailTitle       = document.getElementById("detailTitle");
const detailMeta        = document.getElementById("detailMeta");
const detailBody        = document.getElementById("detailBody");
const detailModalHeader = document.getElementById("detailModalHeader");

// Toast
const toastEl = document.getElementById("toastEl");

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
    page:       1,
    totalPages: window.INITIAL_DATA?.totalPages || 1,
    hasNext:    window.INITIAL_DATA?.hasNext    || false,
    loading:    false,
    search:     "",
    actionType: "",
    dateFrom:   "",
    dateTo:     "",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function debounce(fn, ms = 400) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function fmt(n) {
    return parseFloat(n || 0).toLocaleString("uz-UZ");
}

function showToast(msg, type = "info") {
    toastEl.textContent = msg;
    toastEl.className   = `toast-msg toast-${type}`;
    toastEl.style.display = "block";
    setTimeout(() => { toastEl.style.display = "none"; }, 3000);
}

// ── Action meta map — keys match CSS .log-dot.sale, .log-badge.sale etc. ──────
const ACTION_META = {
    sale:           { label: "Sotuv",              icon: "fa-shopping-cart" },
    sale_return:    { label: "Qaytarish",           icon: "fa-undo"          },
    payment:        { label: "To'lov",              icon: "fa-credit-card"   },
    payment_refund: { label: "To'lov qaytarildi",   icon: "fa-undo-alt"      },
    product_create: { label: "Mahsulot qo'shildi",  icon: "fa-plus"          },
    product_update: { label: "Mahsulot yangilandi", icon: "fa-edit"          },
    product_delete: { label: "Mahsulot o'chirildi", icon: "fa-trash"         },
    stock_add:      { label: "Kirim",               icon: "fa-boxes"         },
    stock_adjust:   { label: "Tuzatish",            icon: "fa-sliders-h"     },
    stock_delete:   { label: "Batch o'chirildi",    icon: "fa-trash"         },
    client_create:  { label: "Mijoz qo'shildi",     icon: "fa-user-plus"     },
    client_update:  { label: "Mijoz yangilandi",    icon: "fa-user-edit"     },
    client_delete:  { label: "Mijoz o'chirildi",    icon: "fa-user-times"    },
};

function getMeta(actionType) {
    return ACTION_META[actionType] || { label: actionType, icon: "fa-circle" };
}

// ── Render a single log item  (classes match history.css exactly) ─────────────
function renderLogItem(log) {
    const meta = getMeta(log.action_type);
    const type = log.action_type; // used as CSS modifier: .log-dot.sale, .log-badge.sale …

    const div = document.createElement("div");
    div.className  = "log-item";
    div.dataset.id = log.id;

    div.innerHTML = `
        <div class="log-timeline">
            <div class="log-dot ${type}">
                <i class="fa ${meta.icon}"></i>
            </div>
        </div>
        <div class="log-body">
            <div class="log-top">
                <span class="log-badge ${type}">${log.action_label || meta.label}</span>
                <span class="log-time">${log.created_at}</span>
            </div>
            <div class="log-desc">${log.description}</div>
            <div class="log-footer">
                <span class="log-user">
                    <i class="fa fa-user-circle"></i> ${log.user || "Tizim"}
                </span>
                <i class="fa fa-chevron-right log-chevron"></i>
            </div>
        </div>
    `;

    div.addEventListener("click", () => openDetail(log));
    return div;
}

// ── Fetch logs from server ────────────────────────────────────────────────────
async function fetchLogs({ page = 1, append = false } = {}) {
    if (state.loading) return;
    state.loading = true;
    if (loadMoreBtn) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.innerHTML = `<i class="fa fa-spinner fa-spin"></i> Yuklanmoqda...`;
    }

    try {
        const url = new URL(window.HISTORY_AJAX_URL, window.location.origin);
        url.searchParams.set("page",       page);
        url.searchParams.set("search",     state.search);
        url.searchParams.set("action_type", state.actionType);
        url.searchParams.set("date_from",  state.dateFrom);
        url.searchParams.set("date_to",    state.dateTo);

        const res  = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        if (!res.ok) throw new Error("Server xatosi: " + res.status);
        const data = await res.json();

        // ── Update state ──
        state.page       = data.page;
        state.totalPages = data.total_pages;
        state.hasNext    = data.has_next;

        // ── Clear or append ──
        if (!append) {
            logList.innerHTML = "";
            // Hide SSR pagination — we use JS now
            if (ssrPagination) ssrPagination.style.display = "none";
        }

        if (data.logs && data.logs.length > 0) {
            const frag = document.createDocumentFragment();
            data.logs.forEach(log => frag.appendChild(renderLogItem(log)));
            logList.appendChild(frag);
        } else if (!append) {
            logList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa fa-history"></i></div>
                    <h3>Hech qanday yozuv topilmadi</h3>
                    <p>Filtrni o'zgartiring yoki qidiruvni tozalang</p>
                </div>`;
        }

        // ── Total count ──
        if (totalNum) totalNum.textContent = data.total_count ?? "—";

        // ── Stats ──
        updateStats(data);

        // ── Load more button ──
        if (loadMoreWrap) {
            loadMoreWrap.style.display = state.hasNext ? "flex" : "none";
        }

    } catch (err) {
        console.error("Log yuklashda xatolik:", err);
        showToast("Ma'lumot yuklanmadi. Qayta urinib ko'ring.", "error");
    } finally {
        state.loading = false;
        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = `<i class="fa fa-chevron-down"></i> Ko'proq yuklash`;
        }
    }
}

// ── Stats row update ──────────────────────────────────────────────────────────
function updateStats(data) {
    // Server may return counts per type in data.counts; fall back to client counts
    const counts = data.counts || {};
    if (cntSale)    cntSale.textContent    = counts.sale    ?? "—";
    if (cntPayment) cntPayment.textContent = counts.payment ?? "—";
    if (cntReturn)  cntReturn.textContent  = counts.sale_return ?? "—";
    if (cntStock)   cntStock.textContent   = counts.stock_add   ?? "—";
}

// ── Detail Modal ──────────────────────────────────────────────────────────────
function openDetail(log) {
    const meta = getMeta(log.action_type);
    const ex   = log.extra_data || {};

    // Header — reuse same CSS classes as list items
    detailIcon.innerHTML = `<i class="fa ${meta.icon}"></i>`;
    detailIcon.className = `detail-icon log-dot ${log.action_type}`;
    detailTitle.textContent = meta.label;
    detailMeta.textContent  = `${log.created_at}  ·  ${log.user || "Tizim"}`;
    detailModalHeader.className = `modal-header`;

    // Body
    detailBody.innerHTML = buildDetailBody(log.action_type, ex, log.description);
    detailModal.show();
}

function row(label, value) {
    if (!value && value !== 0) return "";
    return `<div class="det-row"><span class="det-label">${label}</span><span class="det-val">${value}</span></div>`;
}

function buildDetailBody(type, ex, desc) {
    let html = `<div class="det-rows">`;

    // Description always first
    html += row("Tavsif", desc);

    switch (type) {

        case "sale":
            html += row("Mijoz", ex.client_name);
            html += row("Jami summa", ex.total_amount ? fmt(ex.total_amount) + " so'm" : null);
            if (ex.items && ex.items.length) {
                html += `</div><h6 class="det-section">Sotilgan mahsulotlar</h6>`;
                html += buildItemsTable(ex.items, ["product","quantity","price","subtotal"],
                                        ["Mahsulot","Soni","Narx","Jami"]);
                html = html + `<div class="det-rows">`;
            }
            break;

        case "sale_return":
            html += row("Mijoz",  ex.client_name);
            html += row("Sababu", ex.reason);
            html += row("Jami",   ex.total ? fmt(ex.total) + " so'm" : null);
            if (ex.items && ex.items.length) {
                html += `</div><h6 class="det-section">Qaytarilgan mahsulotlar</h6>`;
                html += buildItemsTable(ex.items, ["product","quantity","price","subtotal"],
                                        ["Mahsulot","Soni","Narx","Jami"]);
                html += `<div class="det-rows">`;
            }
            break;

        case "payment":
            html += row("Mijoz",   ex.client_name);
            html += row("Summa",   ex.amount ? fmt(ex.amount) + " so'm" : null);
            html += row("Izoh",    ex.note);
            break;

        case "payment_refund":
            html += row("Mijoz",   ex.client_name);
            html += row("Summa",   ex.amount ? fmt(ex.amount) + " so'm" : null);
            html += row("Sabab",   ex.reason);
            break;

        case "stock_add":
            html += row("Mahsulot",    ex.product);
            html += row("Miqdor",      ex.quantity ? ex.quantity + " ta" : null);
            html += row("Tannarx",     ex.cost_price ? fmt(ex.cost_price) + " so'm" : null);
            html += row("Jami xarajat", ex.total_cost ? fmt(ex.total_cost) + " so'm" : null);
            break;

        case "stock_adjust":
            html += row("Mahsulot",    ex.product);
            html += row("Tur",         ex.adjustment_type);
            html += row("O'zgarish",   ex.quantity_change !== undefined ? ex.quantity_change + " ta" : null);
            html += row("Yangi narx",  ex.new_cost_price ? fmt(ex.new_cost_price) + " so'm" : null);
            html += row("Sabab",       ex.reason);
            break;

        case "product_create":
        case "product_update":
            html += row("Mahsulot",  ex.name);
            html += row("Narx",      ex.price ? fmt(ex.price) + " so'm" : null);
            html += row("Qoldiq",    ex.stock !== undefined ? ex.stock + " ta" : null);
            break;

        case "product_delete":
            html += row("Mahsulot", ex.name);
            break;

        case "client_create":
        case "client_update":
            html += row("Ism",    ex.name);
            html += row("Telefon", ex.phone);
            html += row("Hudud",  ex.region);
            break;

        case "client_delete":
            html += row("Ism", ex.name);
            break;

        default:
            // Show raw key-value for unknown types
            Object.entries(ex).forEach(([k, v]) => {
                if (typeof v !== "object") html += row(k, v);
            });
    }

    html += `</div>`;
    return html;
}

function buildItemsTable(items, keys, headers) {
    let t = `<div class="det-table-wrap"><table class="det-table">
        <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>`;
    items.forEach(item => {
        t += `<tr>${keys.map(k => {
            let v = item[k] ?? "";
            if (k === "price" || k === "subtotal") v = fmt(v) + " so'm";
            if (k === "quantity") v = v + " ta";
            return `<td>${v}</td>`;
        }).join("")}</tr>`;
    });
    t += `</tbody></table></div>`;
    return t;
}

// ── Filter: type chips ────────────────────────────────────────────────────────
typeChips.addEventListener("click", e => {
    const chip = e.target.closest(".type-chip");
    if (!chip) return;
    typeChips.querySelectorAll(".type-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    state.actionType = chip.dataset.type || "";
    fetchLogs({ page: 1 });
});

// ── Filter: search ────────────────────────────────────────────────────────────
searchInput.addEventListener("input", debounce(() => {
    state.search = searchInput.value.trim();
    searchClear.style.display = state.search ? "flex" : "none";
    fetchLogs({ page: 1 });
}));

searchClear.addEventListener("click", () => {
    searchInput.value   = "";
    state.search        = "";
    searchClear.style.display = "none";
    fetchLogs({ page: 1 });
});

// ── Filter: dates ─────────────────────────────────────────────────────────────
function onDateChange() {
    state.dateFrom = dateFrom.value;
    state.dateTo   = dateTo.value;
    dateClear.style.display = (state.dateFrom || state.dateTo) ? "flex" : "none";
    fetchLogs({ page: 1 });
}
dateFrom.addEventListener("change", onDateChange);
dateTo.addEventListener("change",   onDateChange);

dateClear.addEventListener("click", () => {
    dateFrom.value = "";
    dateTo.value   = "";
    state.dateFrom = "";
    state.dateTo   = "";
    dateClear.style.display = "none";
    fetchLogs({ page: 1 });
});

// ── Load more ─────────────────────────────────────────────────────────────────
loadMoreBtn.addEventListener("click", () => {
    if (state.hasNext) fetchLogs({ page: state.page + 1, append: true });
});

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    // Hide SSR content — JS will take over
    logList.innerHTML = "";
    dateClear.style.display  = "none";
    searchClear.style.display = "none";
    if (loadMoreWrap) loadMoreWrap.style.display = "none";
    fetchLogs({ page: 1 });
});