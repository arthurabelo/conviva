(function () {
    const panel = document.getElementById("active-vote-panel");
    const meetingId = window.CONVIVA_MEETING_ID;
    if (!panel || !meetingId) return;

    async function refreshPanel() {
        try {
            const response = await fetch(`/api/reunioes/${meetingId}/votacao-ativa`, {
                headers: { "Accept": "application/json" }
            });
            if (!response.ok) return;
            const data = await response.json();
            const currentId = panel.querySelector("[data-active-vote]")?.dataset.activeVote || "";
            const nextId = extractVoteId(data.html);
            if (currentId !== nextId || !panel.querySelector("[data-vote-form]")) {
                panel.innerHTML = data.html;
                attachVoteForms();
            }
        } catch (error) {
            console.warn("Falha ao atualizar votacao ativa", error);
        }
    }

    function extractVoteId(html) {
        const match = html.match(/data-active-vote="(\d+)"/);
        return match ? match[1] : "";
    }

    function attachVoteForms() {
        panel.querySelectorAll("[data-vote-form]").forEach((form) => {
            if (form.dataset.bound === "1") return;
            form.dataset.bound = "1";
            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                const voteId = form.closest("[data-active-vote]")?.dataset.activeVote;
                if (!voteId) return;
                const response = await fetch(`/api/votacoes/${voteId}/votar`, {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json" },
                    body: new URLSearchParams(new FormData(form)).toString()
                });
                const data = await response.json();
                panel.innerHTML = data.html;
                attachVoteForms();
            });
        });
    }

    function tickCountdowns() {
        panel.querySelectorAll("[data-countdown]").forEach((node) => {
            let seconds = Number(node.dataset.countdown || "0");
            if (seconds > 0) seconds -= 1;
            node.dataset.countdown = String(seconds);
            const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
            const rest = String(seconds % 60).padStart(2, "0");
            node.textContent = `${minutes}:${rest}`;
        });
    }

    attachVoteForms();
    setInterval(refreshPanel, 1000);
    setInterval(tickCountdowns, 1000);
})();
