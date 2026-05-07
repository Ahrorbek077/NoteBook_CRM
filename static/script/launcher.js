// ================= CSRF =================
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// ================= HELPERS =================
function qs(id) {
    return document.getElementById(id);
}

function showFlash(message) {
    const flash = qs("successFlash");
    const text = qs("successText");

    text.textContent = message;
    flash.classList.remove("d-none");

    setTimeout(() => {
        flash.classList.add("d-none");
    }, 2500);
}

function setLoading(btn, state, text = "Saqlanmoqda...") {
    if (state) {
        btn.disabled = true;
        btn.dataset.original = btn.innerHTML;
        btn.innerHTML = `<i class="fa fa-spinner fa-spin"></i> ${text}`;
    } else {
        btn.disabled = false;
        btn.innerHTML = btn.dataset.original;
    }
}

function clearErrors(form) {
    form.querySelectorAll(".error-text").forEach(e => e.remove());
    form.querySelectorAll(".sf-input").forEach(i => {
        i.style.borderColor = "";
    });
}

function showFieldErrors(form, errors) {
    Object.entries(errors).forEach(([field, msgs]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (!input) return;

        input.style.borderColor = "#ef5350";

        const err = document.createElement("div");
        err.className = "error-text";
        err.style.fontSize = "0.7rem";
        err.style.color = "#ef5350";
        err.style.marginTop = "4px";
        err.textContent = msgs.join(", ");

        input.closest(".sf-field")?.appendChild(err);
    });
}

// ================= MODAL =================
function openModal(el) {
    el.classList.remove("d-none");
    setTimeout(() => {
        el.querySelector("input, select")?.focus();
    }, 150);
}

function closeModal(el) {
    el.classList.add("d-none");
}
// RaSM UCHUN
const imageInput = qs("productImageInput");
const preview = qs("imagePreview");

imageInput?.addEventListener("change", function () {
    const file = this.files[0];

    if (!file) {
        preview.style.display = "none";
        return;
    }

    const reader = new FileReader();

    reader.onload = function (e) {
        preview.src = e.target.result;
        preview.style.display = "block";
    };

    reader.readAsDataURL(file);
});
// open buttons
qs("openClientModal")?.addEventListener("click", () => openModal(qs("clientModal")));
qs("openProductModal")?.addEventListener("click", () => openModal(qs("productModal")));

// close buttons
document.querySelectorAll("[data-close]").forEach(btn => {
    btn.addEventListener("click", () => {
        closeModal(qs(btn.dataset.close));
    });
});

// backdrop click close
document.querySelectorAll(".modal-veil").forEach(veil => {
    veil.addEventListener("click", (e) => {
        if (e.target === veil) closeModal(veil);
    });
});

// ================= UNIVERSAL AJAX SUBMIT =================
async function submitForm({
    form,
    url,
    submitBtn,
    modal,
    successMessage,
    afterSuccess = null
}) {
    clearErrors(form);
    setLoading(submitBtn, true);

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRFToken()
            },
            body: new FormData(form)
        });

        const data = await res.json();

        if (data.status === "created") {
            form.reset();
            closeModal(modal);
            showFlash(successMessage);

            if (afterSuccess) afterSuccess(data);
        } else {
            showFieldErrors(form, data.errors || {});
        }

    } catch (err) {
        console.error(err);
    }

    setLoading(submitBtn, false);
}

// ================= CLIENT =================
const clientForm = qs("clientCreateForm");

clientForm?.addEventListener("submit", (e) => {
    e.preventDefault();

    submitForm({
        form: clientForm,
        url: window.LAUNCHER_URLS.clientCreate,
        submitBtn: qs("clientSubmit"),
        modal: qs("clientModal"),
        successMessage: "Mijoz qo'shildi ✅"
    });
});

// ================= PRODUCT =================
const productForm = qs("productCreateForm");

productForm?.addEventListener("submit", (e) => {
    e.preventDefault();

    submitForm({
        form: productForm,
        url: window.LAUNCHER_URLS.productCreate,
        submitBtn: qs("productSubmit"),
        modal: qs("productModal"),
        successMessage: "Mahsulot qo'shildi 🟡",

        afterSuccess: (data) => {
            console.log("NEW PRODUCT:", data);

            // 🔥 bonus: live qo‘shish (keyinchalik gridga)
            // addProductToUI(data)
        }
    });
});