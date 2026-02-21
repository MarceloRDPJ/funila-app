const API_URL = "https://funila-app.onrender.com";

function getQueryParams() {
    return new URLSearchParams(window.location.search);
}

document.addEventListener("DOMContentLoaded", async () => {
    const params = getQueryParams();
    const clientId = params.get("c") || params.get("client_id");
    const sessionId = params.get("sid");

    // Configura o link do botão
    const ctaBtn = document.getElementById("cta-button");
    if (ctaBtn) {
        // Redireciona para o formulário mantendo todos os parâmetros
        // Assume estrutura de pastas: /frontend/landing/index.html e /frontend/form/index.html
        ctaBtn.href = `../form/index.html?${params.toString()}`;

        ctaBtn.addEventListener("click", () => {
            trackEvent("cta_click", {
                destination: ctaBtn.href
            });
        });
    }

    // Rastreia visualização da página
    if (sessionId) {
        trackEvent("page_view");
    }

    // Carrega dados do cliente para personalizar título
    if (clientId) {
        try {
            const res = await fetch(`${API_URL}/forms/config/${clientId}`);
            if (res.ok) {
                const config = await res.json();
                if (config.client_name) {
                    const titleEl = document.getElementById("client-title");
                    if (titleEl) {
                        // Se o elemento existir, personalizamos. Se for default, mantém o texto padrão.
                        // Mas o user pediu landing padrão, talvez não queira mudar o título principal "Sua análise..."
                        // Vou manter a lógica original: document.title muda, e se houver elemento específico pode mudar.
                    }
                    document.title = `${config.client_name} - Oportunidade Exclusiva`;
                }
            }
        } catch (e) {
            console.error("Erro ao carregar config", e);
        }
    }
});

async function trackEvent(eventType, metadata = {}) {
    const params = getQueryParams();
    const sessionId = params.get("sid");
    const linkId = params.get("l") || params.get("link_id");

    if (!sessionId) return;

    const payload = {
        session_id:  sessionId,
        link_id:     linkId,
        event_type:  eventType,
        metadata:    metadata
    };

    try {
        await fetch(`${API_URL}/funnel/event`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.warn("Tracking error", e);
    }
}
