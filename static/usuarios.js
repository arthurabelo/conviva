(function () {
    const form = document.getElementById("lot-form");
    if (!form) return;

    const tableContainer = document.getElementById("lots-table-container");
    const feedback = document.getElementById("lot-feedback");
    const idInput = document.getElementById("id_lote");
    const nameInput = document.getElementById("identificacao");
    const weightInput = document.getElementById("peso_original");
    const debtInput = document.getElementById("inadimplente");
    const preview = document.getElementById("effective-preview");
    const title = document.getElementById("lot-form-title");
    const submit = document.getElementById("lot-submit");
    const cancel = document.getElementById("cancel-lot-edit");

    function showMessage(message, kind) {
        const box = document.createElement("div");
        box.className = "alert " + kind;
        box.textContent = message;
        feedback.replaceChildren(box);
    }

    function updatePreview() {
        const weight = Number.parseFloat(weightInput.value) || 0;
        preview.textContent = (debtInput.value === "1" ? 0 : weight).toFixed(2);
    }

    function resetForm() {
        form.reset();
        idInput.value = "";
        weightInput.value = "1.00";
        title.textContent = "Vincular novo lote/unidade";
        submit.textContent = "Vincular lote";
        cancel.classList.add("hidden");
        updatePreview();
    }

    function bindTableActions() {
        tableContainer.querySelectorAll("[data-lote-edit]").forEach((button) => {
            button.addEventListener("click", () => {
                idInput.value = button.dataset.id;
                nameInput.value = button.dataset.identificacao;
                weightInput.value = button.dataset.peso;
                debtInput.value = button.dataset.inadimplente;
                title.textContent = "Editar lote/unidade";
                submit.textContent = "Salvar vínculo";
                cancel.classList.remove("hidden");
                updatePreview();
                form.scrollIntoView({ behavior: "smooth", block: "center" });
                nameInput.focus();
            });
        });

        tableContainer.querySelectorAll("[data-lote-delete]").forEach((button) => {
            button.addEventListener("click", async () => {
                if (!window.confirm("Confirma a quebra deste vínculo?")) return;
                button.disabled = true;
                try {
                    const response = await fetch(`/api/usuarios/${button.dataset.owner}/lotes/${button.dataset.loteDelete}/excluir`, { method: "POST" });
                    const payload = await response.json();
                    if (!response.ok) throw new Error(payload.message || "Não foi possível excluir o lote.");
                    tableContainer.innerHTML = payload.html;
                    bindTableActions();
                    resetForm();
                    showMessage(payload.message, "success");
                } catch (error) {
                    showMessage(error.message, "error");
                    button.disabled = false;
                }
            });
        });
    }

    weightInput.addEventListener("input", updatePreview);
    debtInput.addEventListener("change", updatePreview);
    cancel.addEventListener("click", resetForm);
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        submit.disabled = true;
        try {
            const response = await fetch(form.action, { method: "POST", body: new FormData(form) });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.message || "Não foi possível salvar o lote.");
            tableContainer.innerHTML = payload.html;
            bindTableActions();
            resetForm();
            showMessage(payload.message, "success");
        } catch (error) {
            showMessage(error.message, "error");
        } finally {
            submit.disabled = false;
        }
    });

    bindTableActions();
    updatePreview();
})();
