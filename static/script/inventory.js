/* =============================================
   INVENTORY JS - Class-based + Cleaned
   ============================================= */

class InventoryManager {
    constructor() {
        this.searchInput = document.getElementById("searchInput");
        this.productList = document.getElementById("productList");

        this.init();
    }

    init() {
        console.log("%cInventory Manager yuklandi ✅", "color: #10b981; font-weight: bold");

        this.bindEvents();
        
        // Agar qidiruv maydonida allaqachon qiymat bo'lsa
        if (this.searchInput && this.searchInput.value.trim() !== "") {
            this.loadProducts(this.searchInput.value.trim());
        }
    }

    // ====================== Yordamchi funksiyalar ======================
    debounce(func, delay = 400) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    hideModalSafely(modalId) {
        const modalEl = document.getElementById(modalId);
        if (!modalEl) return;

        if (document.activeElement) document.activeElement.blur();

        setTimeout(() => {
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modal.hide();
        }, 10);
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // ====================== Mahsulot kartasini yaratish (Yangi dizaynga mos) ======================
    createProductCard(product) {
        const imageHtml = product.image 
            ? `<img src="${product.image}" class="product-img" alt="${product.name}">` 
            : `<div class="product-img no-image">📦</div>`;

        return `
            <div class="inventory-card" data-id="${product.id}">
                <div class="card-content">
                    ${imageHtml}
                    <div class="product-info">
                        <h5>${product.name}</h5>
                        <div class="product-details">
                            <p class="stock-line">
                                <strong>Stock:</strong> 
                                <span class="stock-number">${product.stock}</span> ta
                            </p>
                            <p class="stock-line">
                                <strong>Sotuv narxi:</strong> 
                                <span class="price">${Number(product.price || 0).toLocaleString('uz-UZ')}</span> so‘m
                            </p>
                            ${product.cost_price && product.cost_price > 0 
                                ? `<p class="stock-line"><strong>Tan narxi:</strong> <span class="cost-price">${Number(product.cost_price).toLocaleString('uz-UZ')}</span> so‘m</p>` 
                                : ''}
                        </div>
                    </div>

                    <button class="collapse-toggle-btn" type="button"
                            data-bs-toggle="collapse" 
                            data-bs-target="#actions${product.id}">
                        <i class="fa fa-chevron-down"></i>
                    </button>
                </div>

                <!-- ACCORDION PANEL -->
                <div id="actions${product.id}" class="collapse actions-panel">
                    <div class="actions-buttons">
                        <button class="action-btn stock-btn" data-product-id="${product.id}">
                            <i class="fa fa-plus"></i> Stok qo‘shish
                        </button>

                        <button class="action-btn history-btn"
                                onclick="window.location.href='/products/product/{{ product.id }}/batches/'">
                            <i class="fa fa-box"></i>
                            Batch / History
                        </button>

                        <button class="action-btn edit-btn" data-id="${product.id}">
                            <i class="fa fa-edit"></i> Tahrirlash
                        </button>
                        <button class="action-btn delete-btn" data-id="${product.id}">
                            <i class="fa fa-trash"></i> O‘chirish
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // ====================== Mahsulotlarni yuklash (AJAX) ======================
    async loadProducts(search = '') {
        if (!this.productList) return;

        try {
            const url = new URL(window.location.href);
            url.searchParams.set('search', search);
            url.searchParams.delete('page');   // qidiruvda sahifani reset qilamiz

            const response = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!response.ok) throw new Error('Server xatosi');

            const data = await response.json();

            this.productList.innerHTML = "";

            if (data.products && data.products.length > 0) {
                data.products.forEach(product => {
                    this.productList.insertAdjacentHTML("beforeend", this.createProductCard(product));
                });
            } else {
                this.productList.innerHTML = `<div class="empty-state"><h3>Hech narsa topilmadi 😕</h3></div>`;
            }

        } catch (error) {
            console.error("Load products error:", error);
            this.productList.innerHTML = `<div class="empty-state"><h3>Xatolik yuz berdi. Qayta yuklab ko‘ring.</h3></div>`;
        }
    }

    // ====================== Eventlar ======================
    bindEvents() {
        // Search
        if (this.searchInput) {
            this.searchInput.addEventListener("keyup", this.debounce(() => {
                this.loadProducts(this.searchInput.value.trim());
            }));
        }

        this.productList.addEventListener("click", (e) => {
            const card = e.target.closest(".inventory-card");
            if (!card) return;
            const productId = card.dataset.id;

            // DELETE
            if (e.target.closest(".delete-btn")) {
                document.getElementById("deleteProductId").value = productId;
                new bootstrap.Modal(document.getElementById("deleteModal")).show();
                return;
            }

            // EDIT / UPDATE
            if (e.target.closest(".edit-btn")) {
                document.getElementById("updateProductId").value = productId;

                const nameEl = card.querySelector("h5");
                const priceEl = card.querySelector(".price");

                if (nameEl) document.getElementById("updateName").value = nameEl.textContent.trim();
                if (priceEl) {
                    const priceText = priceEl.textContent.replace(/[^0-9.]/g, '').trim();
                    document.getElementById("updatePrice").value = priceText || "0";
                }

                new bootstrap.Modal(document.getElementById("updateModal")).show();
            }

            // Stok qo‘shish tugmasi
            if (e.target.closest(".stock-btn")) {
                const productId = e.target.closest(".stock-btn").dataset.productId;

                document.getElementById("stockProductId").value = productId;

                const modal = new bootstrap.Modal(document.getElementById("stockModal"));
                modal.show();
            }
        });

        // Delete form submit
        const deleteForm = document.querySelector("#deleteModal form");
        if (deleteForm) {
            deleteForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(deleteForm);

                try {
                    const response = await fetch(deleteForm.action, {
                        method: "POST",
                        body: formData
                    });
                    const data = await response.json();

                    if (data.status === "deleted") {
                        const id = formData.get("product_id");
                        const card = document.querySelector(`[data-id="${id}"]`);
                        if (card) card.remove();
                        this.hideModalSafely("deleteModal");
                    } else {
                        alert(data.message || "O‘chirishda xatolik");
                    }
                } catch (error) {
                    console.error("Delete error:", error);
                    alert("Server xatosi");
                }
            });
        }

        // Update form submit
        const updateForm = document.querySelector("#updateModal form");
        if (updateForm) {
            updateForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const formData = new FormData(updateForm);

                try {
                    const response = await fetch(updateForm.action, {
                        method: "POST",
                        body: formData
                    });
                    const data = await response.json();

                    if (data.status === "updated") {
                        const id = formData.get("product_id");
                        const card = document.querySelector(`[data-id="${id}"]`);

                        if (card) {
                            const nameEl = card.querySelector("h5");
                            const priceEl = card.querySelector(".price");

                            if (nameEl) nameEl.textContent = formData.get("name") || "";
                            if (priceEl) {
                                priceEl.textContent = Number(formData.get("price") || 0).toLocaleString('uz-UZ');
                            }
                        }

                        this.hideModalSafely("updateModal");

                        // Qidiruv holatini saqlab, ro‘yxatni yangilash
                        const currentSearch = this.searchInput ? this.searchInput.value.trim() : '';
                        this.loadProducts(currentSearch);
                    } else {
                        alert(data.message || "Yangilashda xatolik");
                    }
                } catch (error) {
                    console.error("Update error:", error);
                    alert("Yangilashda server xatosi yuz berdi");
                }
            });
        }

        // STOCK ADD FORM
        const stockForm = document.getElementById("stockAddForm");

        if (stockForm) {
            stockForm.addEventListener("submit", async (e) => {
                e.preventDefault();

                const productId = document.getElementById("stockProductId").value;
                const formData = new FormData(stockForm);

                try {
                    const response = await fetch(`/products/stock/add/${productId}/`, {
                        method: "POST",
                        body: formData,
                        headers: {
                            "X-CSRFToken": this.getCSRFToken()
                        }
                    });

                    const data = await response.json();

                    if (data.status === "success") {

                        // 🔥 UI ni yangilash
                        const card = document.querySelector(`.inventory-card[data-id="${productId}"]`);
                        if (card) {
                            const stockEl = card.querySelector(".stock-number");
                            if (stockEl) stockEl.textContent = data.new_stock;
                        }

                        alert(data.message || "Stok qo‘shildi");

                        stockForm.reset();
                        this.hideModalSafely("stockModal");

                    } else {
                        alert(data.message || "Xatolik");
                    }

                } catch (err) {
                    console.error(err);
                    alert("Server xatosi");
                }
            });
        }

        // Cancel tugmalari
        document.getElementById("cancelDelete")?.addEventListener("click", () => this.hideModalSafely("deleteModal"));
        document.getElementById("cancelUpdate")?.addEventListener("click", () => this.hideModalSafely("updateModal"));

        // Modal close tugmalari
        document.addEventListener("click", (e) => {
            if (e.target.classList.contains("btn-close")) {
                const modal = e.target.closest(".modal");
                if (modal) this.hideModalSafely(modal.id);
            }
        });
    }
}

// ====================== Sahifa yuklanganda ishga tushirish ======================
document.addEventListener("DOMContentLoaded", () => {
    new InventoryManager();
});