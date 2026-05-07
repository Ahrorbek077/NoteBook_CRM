'use strict';

class ClientManager {
    constructor() {
        this.searchInput   = document.getElementById('searchInput');
        this.searchClear   = document.getElementById('searchClear');
        this.clientList    = document.getElementById('clientList');
        this.totalCount    = document.getElementById('totalCount');
        this.statTotalDebt = document.getElementById('statTotalDebt');
        this.statAdvance   = document.getElementById('statTotalAdvance');
        this.statCount     = document.getElementById('statCount');

        this.addModal    = document.getElementById('addClientModal');
        this.editModal   = document.getElementById('editClientModal');
        this.deleteModal = document.getElementById('deleteClientModal');

        this.currentRegion = new URLSearchParams(window.location.search).get('region') || '';
        this.currentSearch = new URLSearchParams(window.location.search).get('search') || '';

        this.init();
    }

    init() {
        console.log('%c✅ ClientManager yuklandi', 'color:#00d4aa;font-weight:bold');
        this.bindEvents();
        this.updateStatsFromDOM();
        this.updateSearchClear();
    }

    // ==================== DEBOUNCE ====================
    debounce(fn, delay = 380) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
    }

    // ==================== CSRF ====================
    getCSRF() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // ==================== FORMAT NUMBER ====================
    fmt(n) {
        return Math.round(n).toLocaleString('uz-UZ');
    }

    // ==================== STATS FROM CURRENT DOM ====================
    updateStatsFromDOM() {
        const cards = this.clientList.querySelectorAll('.client-card');
        let totalDebt = 0, totalAdvance = 0;

        cards.forEach(card => {
            totalDebt    += parseFloat(card.dataset.debt    || 0);
            totalAdvance += parseFloat(card.dataset.advance || 0);
        });

        if (this.statTotalDebt)  this.statTotalDebt.textContent  = this.fmt(totalDebt) + ' so\'m';
        if (this.statAdvance)    this.statAdvance.textContent     = this.fmt(totalAdvance) + ' so\'m';
        if (this.statCount)      this.statCount.textContent       = cards.length;
    }

    // ==================== UPDATE STATS FROM API DATA ====================
    updateStats(clients) {
        let totalDebt = 0, totalAdvance = 0;
        clients.forEach(c => {
            totalDebt    += c.total_debt    || 0;
            totalAdvance += c.advance_balance || 0;
        });
        if (this.statTotalDebt) this.statTotalDebt.textContent  = this.fmt(totalDebt) + ' so\'m';
        if (this.statAdvance)   this.statAdvance.textContent    = this.fmt(totalAdvance) + ' so\'m';
        if (this.statCount)     this.statCount.textContent      = clients.length;
    }

    // ==================== SEARCH CLEAR BUTTON ====================
    updateSearchClear() {
        if (!this.searchClear) return;
        this.searchClear.style.display = this.searchInput?.value ? 'flex' : 'none';
    }

    // ==================== BUILD CLIENT CARD HTML ====================
    buildCard(c) {
        const debt    = parseFloat(c.total_debt || 0);
        const advance = parseFloat(c.advance_balance || 0);

        let badgeHtml, labelHtml;
        if (debt > 0) {
            badgeHtml = `<span class="balance-badge debt">-${this.fmt(debt)}</span>`;
            labelHtml = 'qarz';
        } else if (advance > 0) {
            badgeHtml = `<span class="balance-badge advance">+${this.fmt(advance)}</span>`;
            labelHtml = 'avans';
        } else {
            badgeHtml = `<span class="balance-badge zero">0</span>`;
            labelHtml = 'toza';
        }

        const regionTag = c.region_name
            ? `<span class="region-tag"><i class="fa fa-map-marker-alt"></i> ${c.region_name}</span>`
            : '';

        const initial = (c.name || '?')[0].toUpperCase();

        return `
        <div class="client-card"
             data-id="${c.id}"
             data-name="${c.name || ''}"
             data-phone="${c.phone || ''}"
             data-address="${c.address || ''}"
             data-region-id="${c.region_id || ''}"
             data-debt="${debt}"
             data-advance="${advance}">

            <div class="card-main" onclick="window.location.href='/clients/client/${c.id}/'">
                <div class="client-avatar">${initial}</div>
                <div class="client-info">
                    <div class="client-name">${c.name}</div>
                    <div class="client-meta">
                        <span><i class="fa fa-phone"></i> ${c.phone}</span>
                        ${regionTag}
                    </div>
                </div>
                <div class="client-balance">
                    ${badgeHtml}
                    <div class="balance-label">${labelHtml}</div>
                </div>
            </div>

            <div class="card-actions">
                <button class="ca-btn view-btn" data-id="${c.id}">
                    <i class="fa fa-eye"></i><span>Ko'rish</span>
                </button>
                <button class="ca-btn edit-btn"
                        data-id="${c.id}"
                        data-name="${c.name || ''}"
                        data-phone="${c.phone || ''}"
                        data-address="${c.address || ''}"
                        data-region-id="${c.region_id || ''}">
                    <i class="fa fa-edit"></i><span>Tahrirlash</span>
                </button>
                <button class="ca-btn delete-btn"
                        data-id="${c.id}"
                        data-name="${c.name || ''}">
                    <i class="fa fa-trash"></i><span>O'chirish</span>
                </button>
            </div>
        </div>`;
    }

    // ==================== LOAD CLIENTS (AJAX) ====================
    async loadClients(search = '', region = '') {
        if (!this.clientList) return;

        this.clientList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="animation: pulse 1s infinite">
                    <i class="fa fa-spinner fa-spin"></i>
                </div>
            </div>`;

        try {
            const url = new URL(window.location.href);
            url.searchParams.set('search', search);
            url.searchParams.set('region', region);
            url.searchParams.delete('page');

            const resp = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!resp.ok) throw new Error(`${resp.status}`);
            const data = await resp.json();

            if (this.totalCount) {
                this.totalCount.textContent = data.total_count + ' ta';
            }

            if (!data.clients || data.clients.length === 0) {
                this.clientList.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon"><i class="fa fa-search"></i></div>
                        <h3>Hech narsa topilmadi</h3>
                        <p>Qidiruv shartlarini o'zgartiring</p>
                    </div>`;
                this.updateStats([]);
                return;
            }

            this.clientList.innerHTML = data.clients.map(c => this.buildCard(c)).join('');
            this.updateStats(data.clients);

        } catch (err) {
            console.error('loadClients error:', err);
            this.clientList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fa fa-exclamation-triangle"></i></div>
                    <h3>Xatolik yuz berdi</h3>
                    <p>Sahifani yangilang</p>
                </div>`;
        }
    }

    // ==================== BIND EVENTS ====================
    bindEvents() {

        // Search input
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(() => {
                this.currentSearch = this.searchInput.value.trim();
                this.updateSearchClear();
                this.loadClients(this.currentSearch, this.currentRegion);
            }));
        }

        // Search clear
        if (this.searchClear) {
            this.searchClear.addEventListener('click', () => {
                this.searchInput.value = '';
                this.currentSearch = '';
                this.updateSearchClear();
                this.loadClients('', this.currentRegion);
                this.searchInput.focus();
            });
        }

        // Region filter chips
        document.querySelectorAll('.region-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.region-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this.currentRegion = chip.dataset.region || '';
                this.loadClients(this.currentSearch, this.currentRegion);
            });
        });

        // Client list — event delegation
        if (this.clientList) {
            this.clientList.addEventListener('click', e => {
                const viewBtn   = e.target.closest('.view-btn');
                const editBtn   = e.target.closest('.edit-btn');
                const deleteBtn = e.target.closest('.delete-btn');

                if (viewBtn) {
                    window.location.href = `/clients/client/${viewBtn.dataset.id}/`;
                    return;
                }
                if (editBtn) {
                    this.openEditModal(editBtn.dataset);
                    return;
                }
                if (deleteBtn) {
                    this.openDeleteModal(deleteBtn.dataset);
                    return;
                }
            });
        }

        // Add form submit
        document.getElementById('addClientForm')?.addEventListener('submit', e => this.handleAdd(e));

        // Edit form submit
        document.getElementById('editClientForm')?.addEventListener('submit', e => this.handleEdit(e));

        // Delete form submit
        document.getElementById('deleteClientForm')?.addEventListener('submit', e => this.handleDelete(e));

        // Add modal — reset on open
        this.addModal?.addEventListener('show.bs.modal', () => {
            document.getElementById('addClientForm')?.reset();
        });
    }

    // ==================== MODAL HELPERS ====================
    openEditModal(data) {
        document.getElementById('editClientId').value  = data.id    || '';
        document.getElementById('editName').value      = data.name  || '';
        document.getElementById('editPhone').value     = data.phone || '';
        document.getElementById('editAddress').value   = data.address || '';
        const regionSel = document.getElementById('editRegion');
        if (regionSel) regionSel.value = data.regionId || '';
        new bootstrap.Modal(this.editModal).show();
    }

    openDeleteModal(data) {
        document.getElementById('deleteClientId').value       = data.id   || '';
        document.getElementById('deleteClientName').textContent = data.name || '';
        new bootstrap.Modal(this.deleteModal).show();
    }

    hideModal(modalEl) {
        const m = bootstrap.Modal.getInstance(modalEl);
        if (m) m.hide();
    }

    // ==================== FORM HANDLERS ====================
    async handleAdd(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'created') {
                this.hideModal(this.addModal);
                form.reset();
                await this.loadClients(this.currentSearch, this.currentRegion);
            } else {
                alert(data.message || 'Xatolik yuz berdi');
            }
        } catch (err) {
            console.error(err);
            alert('Server bilan xatolik');
        } finally {
            btn.disabled = false;
        }
    }

    async handleEdit(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'updated') {
                this.hideModal(this.editModal);
                await this.loadClients(this.currentSearch, this.currentRegion);
            } else {
                alert(data.message || 'Xatolik yuz berdi');
            }
        } catch (err) {
            console.error(err);
            alert('Tahrirlashda xatolik');
        } finally {
            btn.disabled = false;
        }
    }

    async handleDelete(e) {
        e.preventDefault();
        const form = e.target;
        const btn  = form.querySelector('[type=submit]');
        btn.disabled = true;

        try {
            const resp = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await resp.json();

            if (data.status === 'deleted') {
                this.hideModal(this.deleteModal);
                await this.loadClients(this.currentSearch, this.currentRegion);
            } else {
                alert(data.message || "O'chirishda xatolik");
            }
        } catch (err) {
            console.error(err);
            alert("O'chirishda xatolik yuz berdi");
        } finally {
            btn.disabled = false;
        }
    }
}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', () => {
    new ClientManager();
});