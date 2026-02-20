(function(window, document) {
    'use strict';

    // Configuração
    const SCRIPT = document.currentScript;
    const CLIENT_ID = SCRIPT ? SCRIPT.getAttribute('data-client') : null;
    const API_URL = "https://funila-app.onrender.com"; // Produção

    if (!CLIENT_ID) {
        console.warn("[Funila] Client ID não configurado no script.");
        return;
    }

    const STATE = {
        startTime: Date.now(),
        scroll50: false,
        scroll90: false,
        url: window.location.href,
        referrer: document.referrer
    };

    // Função de envio (Beacon / Fetch Keepalive)
    function sendEvent(type, meta = {}) {
        const payload = {
            client_id: CLIENT_ID,
            event_type: type,
            page_url: STATE.url,
            metadata: {
                time_on_page: Date.now() - STATE.startTime,
                referrer: STATE.referrer,
                user_agent: navigator.userAgent,
                screen_width: window.screen.width,
                ...meta
            }
        };

        const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });

        // Tenta Beacon primeiro
        if (navigator.sendBeacon) {
            const success = navigator.sendBeacon(`${API_URL}/scanner/event`, blob);
            if (success) return;
        }

        // Fallback Fetch Keepalive
        fetch(`${API_URL}/scanner/event`, {
            method: 'POST',
            body: JSON.stringify(payload),
            headers: { 'Content-Type': 'application/json' },
            keepalive: true
        }).catch(() => {});
    }

    // 1. Page View
    sendEvent("page_view");

    // 2. Scroll Tracking (Throttle)
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) return;
        scrollTimeout = setTimeout(() => {
            const scrollTop = window.scrollY;
            const docHeight = document.body.offsetHeight;
            const winHeight = window.innerHeight;
            const scrollPercent = (scrollTop / (docHeight - winHeight)) * 100;

            if (scrollPercent > 50 && !STATE.scroll50) {
                STATE.scroll50 = true;
                sendEvent("scroll_50");
            }
            if (scrollPercent > 90 && !STATE.scroll90) {
                STATE.scroll90 = true;
                sendEvent("scroll_90");
            }
            scrollTimeout = null;
        }, 200);
    });

    // 3. Button Clicks (Delegation)
    document.addEventListener('click', (e) => {
        const target = e.target.closest('[data-funila-track]');
        if (target) {
            const label = target.innerText || target.id || "button";
            sendEvent("button_click", { label: label, id: target.id });
        }
    });

    // 4. Time on Page / Exit (Visibility & Unload)
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === 'hidden') {
            sendEvent("time_on_page");
        }
    });

    // 5. Exposição Global para captura manual (Lead)
    window.Funila = {
        captureLead: function(leadData) {
            // leadData: { email, phone, name ... }
            // Opcional: enviar evento específico ou chamar API de lead
            sendEvent("lead_capture", leadData);
        }
    };

})(window, document);
