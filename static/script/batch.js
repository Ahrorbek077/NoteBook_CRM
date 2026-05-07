'use strict';

// ==================== TOAST ====================
function showToast(msg, type = 'success', duration = 3000) {
    const el = document.getElementById('toastEl');
    if (!el) return;
    el.textContent = msg;
    el.className = `toast-msg ${type}`;
    el.style.display = 'block';
    clearTimeout(el._timer);
    el._timer = setTimeout(() => { el.style.display = 'none'; }, duration);
}

// ==================== FORMAT ====================
function fmt(n) {
    return Math.round(n).toLocaleString('uz-UZ');
}

function getCSRF() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// ==================== ADJUSTMENT TYPE LABELS ====================
const TYPE_LABELS = {
    increase:     { label: 'Miqdor oshirildi',   icon: 'fa-arrow-up',      cls: 'increase' },
    decrease:     { label: 'Miqdor kamaytirildi', icon: 'fa-arrow-down',    cls: 'decrease' },
    price_change: { label: 'Narx o\'zgartirildi', icon: 'fa-tag',           cls: 'price_change' },
    correction:   { label: 'Tuzatish',            icon: 'fa-wrench',        cls: 'correction' },
    return:       { label: 'Sotuv qaytarildi',    icon: 'fa-undo',          cls: 'return' },
};

// ==================== RENDER ADJUSTMENT HISTORY ====================
function renderAdjHistory(batchId, adjustments) {
    const container = document.getElementById(`adj-${batchId}`);
    if (!container) return;

    if (!adjustments || adjustments.length === 0) {
        container.innerHTML = `
            <div class="adj-header">Tuzatishlar tarixi</div>
            <div style="text-align:center;color:var(--text-muted);font-size:0.8rem;padding:10px 0">
                Hali tuzatish yo'q
            </div>`;
        return;
    }

    let html = `<div class="adj-header">Tuzatishlar tarixi (${adjustments.length} ta)</div>`;

    adjustments.forEach(adj => {
        const t = TYPE_LABELS[adj.adjustment_type] || { label: adj.adjustment_type, icon: 'fa-circle', cls: 'increase' };

        let qtyHtml = '';
        if (adj.quantity_change !== null && adj.quantity_change !== 0) {
            const cls = adj.quantity_change > 0 ? 'pos' : 'neg';
            const sign = adj.quantity_change > 0 ? '+' : '';
            qtyHtml = `<span class="adj-qty ${cls}">${sign}${adj.quantity_change} ta</span>`;
        }
        if (adj.new_cost_price) {
            qtyHtml += `<span class="adj-qty" style="color:var(--orange)">${fmt(adj.new_cost_price)} so'm</span>`;
        }

        html += `
        <div class="adj-item">
            <div class="adj-type-icon ${t.cls}">
                <i class="fa ${t.icon}"></i>
            </div>
            <div class="adj-body">
                <div class="adj-type-label">${t.label}</div>
                <div class="adj-meta">
                    ${qtyHtml}
                    ${adj.reason ? `<span class="adj-reason" title="${adj.reason}">· ${adj.reason}</span>` : ''}
                </div>
            </div>
            <div class="adj-date">${adj.created_at}</div>
        </div>`;
    });

    container.innerHTML = html;
}

// ==================== LOAD ADJ HISTORY ====================
async function loadAdjHistory(batchId) {
    const container = document.getElementById(`adj-${batchId}`);
    if (!container) return;

    container.innerHTML = `<div class="adj-loading"><i class="fa fa-spinner fa-spin"></i> Yuklanmoqda...</div>`;
    container.classList.remove('d-none');

    try {
        const url = URLS.adjHistory.replace('/0/', `/${batchId}/`);
        const resp = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await resp.json();

        if (data.status === 'success') {
            renderAdjHistory(batchId, data.adjustments);
        } else {
            container.innerHTML = `<div class="adj-loading" style="color:var(--red)">${data.message}</div>`;
        }
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="adj-loading" style="color:var(--red)">Yuklashda xatolik</div>`;
    }
}

// ==================== UPDATE BATCH CARD IN DOM ====================
function updateBatchCard(batchId, data) {
    const card = document.getElementById(`batch-${batchId}`);
    if (!card) return;

    // update data attrs
    card.dataset.remaining = data.new_remaining ?? card.dataset.remaining;
    card.dataset.cost      = data.new_cost_price ?? card.dataset.cost;

    // Reload page for simplicity (full state sync)
    // In production you could do surgical DOM update here
    location.reload();
}

// ==================== ADD STOCK ====================
document.addEventListener('DOMContentLoaded', () => {

    // Open add stock modal
    document.getElementById('openAddStock')?.addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('addStockModal'));
        document.getElementById('addStockForm').reset();
        document.getElementById('calcValue').textContent = '—';
        modal.show();
    });

    // Calc preview
    function updateCalc() {
        const qty  = parseInt(document.getElementById('addQty')?.value || 0);
        const cost = parseFloat(document.getElementById('addCost')?.value || 0);
        const el   = document.getElementById('calcValue');
        if (el) {
            el.textContent = (qty > 0 && cost > 0)
                ? fmt(qty * cost) + ' so\'m'
                : '—';
        }
    }
    document.getElementById('addQty')?.addEventListener('input', updateCalc);
    document.getElementById('addCost')?.addEventListener('input', updateCalc);

    // Add stock submit
    document.getElementById('addStockForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('addStockSubmit');
        btn.disabled = true;

        try {
            const form = e.target;
            const resp = await fetch(URLS.addStock, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-CSRFToken': getCSRF(), 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast(data.message, 'success');
                bootstrap.Modal.getInstance(document.getElementById('addStockModal'))?.hide();
                setTimeout(() => location.reload(), 800);
            } else {
                showToast(data.message || 'Xatolik', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Server bilan xatolik', 'error');
        } finally {
            btn.disabled = false;
        }
    });

    // ==================== BATCH LIST EVENT DELEGATION ====================
    document.getElementById('batchList')?.addEventListener('click', async (e) => {

        // ADJUST btn
        const adjustBtn = e.target.closest('.adjust-btn');
        if (adjustBtn) {
            const d = adjustBtn.dataset;
            openAdjustModal(d.id, d.remaining, d.received, d.cost);
            return;
        }

        // HISTORY btn
        const historyBtn = e.target.closest('.history-btn');
        if (historyBtn) {
            const batchId = historyBtn.dataset.id;
            const adjDiv  = document.getElementById(`adj-${batchId}`);

            if (adjDiv.classList.contains('d-none')) {
                await loadAdjHistory(batchId);
                historyBtn.style.color = 'var(--accent)';
            } else {
                adjDiv.classList.add('d-none');
                historyBtn.style.color = '';
            }
            return;
        }

        // DELETE btn
        const deleteBtn = e.target.closest('.delete-btn');
        if (deleteBtn) {
            openDeleteModal(deleteBtn.dataset.id);
            return;
        }
    });

    // ==================== ADJUST MODAL ====================
    function openAdjustModal(batchId, remaining, received, cost) {
        document.getElementById('adjustBatchId').value = batchId;
        document.getElementById('adjCurRemaining').textContent = remaining + ' ta';
        document.getElementById('adjCurCost').textContent = fmt(cost) + ' so\'m';
        document.getElementById('adjQtyChange').value = 0;
        document.getElementById('adjNewCost').value = '';
        document.getElementById('adjReason').value = '';
        document.getElementById('adjQtyPreview').textContent = '';
        document.getElementById('adjPricePreview').textContent = '';

        // Store for preview calc
        document.getElementById('adjustModal').dataset.remaining = remaining;
        document.getElementById('adjustModal').dataset.cost = cost;

        // Reset tabs
        switchAdjTab('qty');

        new bootstrap.Modal(document.getElementById('adjustModal')).show();
    }

    // Tab switch
    function switchAdjTab(tab) {
        document.querySelectorAll('.adj-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.adj-tab[data-tab="${tab}"]`)?.classList.add('active');

        document.getElementById('tabQty').classList.toggle('d-none', tab !== 'qty');
        document.getElementById('tabPrice').classList.toggle('d-none', tab !== 'price');
    }

    document.querySelectorAll('.adj-tab').forEach(tab => {
        tab.addEventListener('click', () => switchAdjTab(tab.dataset.tab));
    });

    // Qty +/- buttons
    document.getElementById('qtyMinus')?.addEventListener('click', () => {
        const input = document.getElementById('adjQtyChange');
        input.value = parseInt(input.value || 0) - 1;
        updateQtyPreview();
    });
    document.getElementById('qtyPlus')?.addEventListener('click', () => {
        const input = document.getElementById('adjQtyChange');
        input.value = parseInt(input.value || 0) + 1;
        updateQtyPreview();
    });
    document.getElementById('adjQtyChange')?.addEventListener('input', updateQtyPreview);
    document.getElementById('adjNewCost')?.addEventListener('input', updatePricePreview);

    function updateQtyPreview() {
        const modal   = document.getElementById('adjustModal');
        const current = parseInt(modal.dataset.remaining || 0);
        const change  = parseInt(document.getElementById('adjQtyChange').value || 0);
        const newVal  = current + change;
        const el = document.getElementById('adjQtyPreview');

        if (change === 0) { el.textContent = ''; return; }

        const sign = change > 0 ? '+' : '';
        const color = change > 0 ? 'var(--green)' : 'var(--red)';

        el.innerHTML = `
            Hozir: <strong>${current}</strong> ta 
            <span style="color:${color}"> ${sign}${change} </span> → 
            <strong style="color:${newVal < 0 ? 'var(--red)' : 'var(--text-primary)'}">${newVal}</strong> ta
            ${newVal < 0 ? ' ⚠️ Manfiy bo\'lib qoladi!' : ''}`;
    }

    function updatePricePreview() {
        const modal    = document.getElementById('adjustModal');
        const current  = parseFloat(modal.dataset.cost || 0);
        const newPrice = parseFloat(document.getElementById('adjNewCost').value || 0);
        const el = document.getElementById('adjPricePreview');

        if (!newPrice) { el.textContent = ''; return; }

        const diff  = newPrice - current;
        const sign  = diff > 0 ? '+' : '';
        const color = diff > 0 ? 'var(--orange)' : 'var(--green)';

        el.innerHTML = `
            Hozir: <strong>${fmt(current)}</strong> → 
            <strong style="color:${color}">${fmt(newPrice)}</strong> so'm 
            (<span style="color:${color}">${sign}${fmt(diff)}</span>)`;
    }

    // Adjust submit
    document.getElementById('adjustForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn     = document.getElementById('adjustSubmit');
        const batchId = document.getElementById('adjustBatchId').value;
        const reason  = document.getElementById('adjReason').value.trim();

        if (!reason) {
            showToast('Sabab kiritish majburiy!', 'error');
            document.getElementById('adjReason').focus();
            return;
        }

        // Which tab is active?
        const activeTab = document.querySelector('.adj-tab.active')?.dataset.tab;
        const formData  = new FormData();
        formData.append('csrfmiddlewaretoken', getCSRF());
        formData.append('reason', reason);

        if (activeTab === 'qty') {
            const qty = parseInt(document.getElementById('adjQtyChange').value || 0);
            if (qty === 0) {
                showToast('Miqdor o\'zgarishini kiriting!', 'error');
                return;
            }
            formData.append('quantity_change', qty);
        } else {
            const newCost = document.getElementById('adjNewCost').value.trim();
            if (!newCost) {
                showToast('Yangi narxni kiriting!', 'error');
                return;
            }
            formData.append('new_cost_price', newCost);
            formData.append('quantity_change', 0);
        }

        btn.disabled = true;

        try {
            const url  = URLS.adjust.replace('/0/', `/${batchId}/`);
            const resp = await fetch(url, {
                method: 'POST',
                body: formData,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast('Muvaffaqiyatli tuzatildi!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('adjustModal'))?.hide();
                setTimeout(() => location.reload(), 800);
            } else {
                showToast(data.message || 'Xatolik', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Server bilan xatolik', 'error');
        } finally {
            btn.disabled = false;
        }
    });

    // ==================== DELETE MODAL ====================
    function openDeleteModal(batchId) {
        document.getElementById('deleteBatchId').value = batchId;
        new bootstrap.Modal(document.getElementById('deleteModal')).show();
    }

    document.getElementById('deleteForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const batchId = document.getElementById('deleteBatchId').value;
        const btn = e.target.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const url  = URLS.deleteBatch.replace('/0/', `/${batchId}/`);
            const resp = await fetch(url, {
                method: 'POST',
                body: new FormData(e.target),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'success') {
                showToast('Batch arxivlandi', 'success');
                bootstrap.Modal.getInstance(document.getElementById('deleteModal'))?.hide();
                setTimeout(() => location.reload(), 800);
            } else {
                showToast(data.message || 'Xatolik', 'error');
            }
        } catch (err) {
            console.error(err);
            showToast('Server bilan xatolik', 'error');
        } finally {
            btn.disabled = false;
        }
    });

});