/**
 * Funila — Motor do Formulário de Qualificação
 *
 * CORREÇÃO CRÍTICA: API_URL corrigida para o domínio real do Render.
 * Erro anterior: "funila-api.onrender.com" (serviço inexistente)
 * Correto:       "funila-app.onrender.com"
 *
 * Funcionalidades implementadas:
 *   - Carregamento dinâmico de configuração do cliente
 *   - Captura parcial ao concluir etapa 1 (lead salvo mesmo com abandono)
 *   - Rastreio de eventos de funil em tempo real
 *   - Validação por etapa com feedback visual
 *   - Máscaras de telefone e CPF
 *   - Submit final com geração do link WhatsApp pré-preenchido
 */

/* ─── Configuração central ─────────────────────────────────────────────── */
// URL CORRIGIDA: era "funila-api.onrender.com" — serviço que não existe.
const API_URL = "https://funila-app.onrender.com";

/* ─── Estado global ─────────────────────────────────────────────────────── */
let currentStep   = 1;     // etapa ativa (1-3; 4 = sucesso)
let clientConfig  = null;  // configuração retornada pela API
let formData      = {};    // respostas acumuladas por etapa
let partialLeadId = null;  // ID do lead salvo na etapa 1
let sessionId     = null;  // session_id do tracker (via URL)
let fieldTimers   = {};    // timestamps de foco por campo
let stepStartTime = null;  // início da etapa atual

/* ─── Captura de parâmetros da URL ─────────────────────────────────────── */
function getQueryParams() {
    const p = new URLSearchParams(window.location.search);
    return {
        client_id:    p.get("c")            || p.get("client_id")  || "",
        link_id:      p.get("l")            || p.get("link_id")    || "",
        session_id:   p.get("sid")          || "",
        utm_source:   p.get("utm_source")   || "",
        utm_medium:   p.get("utm_medium")   || "",
        utm_campaign: p.get("utm_campaign") || "",
        utm_content:  p.get("utm_content")  || "",
        utm_term:     p.get("utm_term")     || "",
    };
}
const queryParams = getQueryParams();

/* ─── Rastreio de eventos ───────────────────────────────────────────────── */
// Envia evento para API de forma assíncrona e silenciosa.
// Jamais bloqueia o fluxo do usuário em caso de falha.
function trackEvent(eventType, extra = {}) {
    if (!queryParams.link_id) return;
    fetch(`${API_URL}/funnel/event`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sessionId || queryParams.session_id || null,
            link_id:    queryParams.link_id,
            event_type: eventType,
            step:       currentStep,
            ...extra,
        }),
    }).catch(() => {});
}

/* ─── Inicialização ─────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
    sessionId     = queryParams.session_id || null;
    stepStartTime = Date.now();

    if (!queryParams.client_id) {
        showFatalError("Link inválido. Solicite um novo link ao responsável.");
        return;
    }

    trackEvent("page_view");

    try {
        const res = await fetch(`${API_URL}/forms/config/${queryParams.client_id}`);
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.detail || `HTTP ${res.status}`);
        }
        clientConfig = await res.json();
        if (!clientConfig.fields || clientConfig.fields.length === 0) {
            throw new Error("Formulário sem campos configurados");
        }
        renderForm(clientConfig);
    } catch (err) {
        console.error("[Funila] Falha ao carregar formulário:", err);
        showFatalError("Não foi possível carregar o formulário. Tente novamente em instantes.");
        return;
    }

    document.getElementById("lead-form").addEventListener("submit", handleSubmit);

    // Rastreia abandono antes da tela de sucesso
    window.addEventListener("beforeunload", () => {
        if (currentStep < 4) {
            trackEvent("form_abandon", {
                metadata: {
                    step_reached:    currentStep,
                    time_on_step_ms: stepStartTime ? Date.now() - stepStartTime : 0,
                },
            });
        }
    });
});

/* ─── Renderização ──────────────────────────────────────────────────────── */
function renderForm(config) {
    const nameEl = document.getElementById("client-name");
    if (nameEl) nameEl.textContent = config.client_name;
    document.title = `${config.client_name} — Qualificação`;

    const step1Keys = ["full_name", "phone", "email"];
    const step3Keys = ["income_range", "tried_financing", "cpf"];
    const step1 = config.fields.filter(f => step1Keys.includes(f.field_key));
    const step3 = config.fields.filter(f => step3Keys.includes(f.field_key));
    const step2 = config.fields.filter(f =>
        !step1Keys.includes(f.field_key) && !step3Keys.includes(f.field_key)
    );

    renderFieldsTo(step1, "fields-step-1");
    renderFieldsTo(step2, "fields-step-2");
    renderFieldsTo(step3, "fields-step-3");
    setupMasks();
    setupFieldTracking();
    updateProgressDots(1);
}

// Renderiza campos em um container específico, ordenado por `order`
function renderFieldsTo(fields, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    [...fields]
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .forEach(field => {
            const group = document.createElement("div");
            group.className = "form-group";

            const lbl = document.createElement("label");
            lbl.setAttribute("for", `field-${field.field_key}`);
            lbl.textContent = field.label + (field.required ? " *" : "");
            group.appendChild(lbl);

            if (field.type === "select" || field.type === "radio") {
                group.appendChild(buildOptionButtons(field));
            } else {
                const input = document.createElement("input");
                input.type = field.field_key === "email" ? "email" : "text";
                input.id   = `field-${field.field_key}`;
                input.name = field.field_key;
                input.placeholder = field.label;
                if (field.required) input.required = true;
                if (field.field_key === "phone")     { input.classList.add("mask-phone"); input.inputMode = "tel"; input.autocomplete = "tel"; }
                if (field.field_key === "cpf")       { input.classList.add("mask-cpf");   input.inputMode = "numeric"; input.autocomplete = "off"; }
                if (field.field_key === "full_name") input.autocomplete = "name";
                if (field.field_key === "email")     input.autocomplete = "email";
                group.appendChild(input);
            }

            // Dica para CPF
            if (field.field_key === "cpf") {
                const hint = document.createElement("span");
                hint.className   = "field-hint";
                hint.textContent = "Opcional — usado para análise de crédito com seu consentimento";
                group.appendChild(hint);
            }

            container.appendChild(group);
        });
}

// Botões de opção substituem selects/radios nativos (UX superior em mobile)
function buildOptionButtons(field) {
    const wrapper = document.createElement("div");
    wrapper.className        = "option-group";
    wrapper.dataset.fieldKey = field.field_key;
    wrapper.dataset.required = field.required ? "true" : "false";

    const hidden = document.createElement("input");
    hidden.type  = "hidden";
    hidden.name  = field.field_key;
    hidden.id    = `field-${field.field_key}`;
    if (field.required) hidden.required = true;
    wrapper.appendChild(hidden);

    let opts = field.options || [];
    if (typeof opts === "string") { try { opts = JSON.parse(opts); } catch { opts = []; } }

    opts.forEach(opt => {
        const btn = document.createElement("button");
        btn.type = "button"; btn.className = "option-btn";
        btn.textContent = opt; btn.dataset.value = opt;
        btn.addEventListener("click", () => {
            wrapper.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
            btn.classList.add("selected");
            hidden.value = opt;
            wrapper.classList.remove("error");
            if (field.field_key === "has_clt") toggleCltYearsGroup(opt === "Sim");
        });
        wrapper.appendChild(btn);
    });
    return wrapper;
}

// Exibe/oculta campo de tempo de CLT com base na seleção
function toggleCltYearsGroup(show) {
    const group = document.querySelector("[data-field-key='clt_years']")?.closest(".form-group");
    if (!group) return;
    group.style.display = show ? "flex" : "none";
    if (!show) {
        const h = group.querySelector("input[type='hidden']");
        if (h) h.value = "";
        group.querySelectorAll(".option-btn").forEach(b => b.classList.remove("selected"));
    }
}

/* ─── Navegação ─────────────────────────────────────────────────────────── */
window.nextStep = async function(step) {
    if (!validateStep(step)) return;
    saveStepData(step);

    if (step === 1) { await savePartialLead(); trackEvent("step_complete", { step: 1 }); }
    else if (step === 2) { trackEvent("step_complete", { step: 2 }); }

    const curr = document.getElementById(`step-${step}`);
    const next = document.getElementById(`step-${step + 1}`);
    if (curr) { curr.classList.remove("active"); curr.classList.add("exiting"); }
    setTimeout(() => curr?.classList.remove("exiting"), 350);
    if (next) next.classList.add("active");
    currentStep = step + 1; stepStartTime = Date.now();
    updateProgressDots(currentStep);
    window.scrollTo({ top: 0, behavior: "smooth" });
};

window.prevStep = function(step) {
    if (step <= 1) return;
    document.getElementById(`step-${step}`)?.classList.remove("active");
    document.getElementById(`step-${step - 1}`)?.classList.add("active");
    currentStep = step - 1; stepStartTime = Date.now();
    updateProgressDots(currentStep);
    window.scrollTo({ top: 0, behavior: "smooth" });
};

function updateProgressDots(step) {
    [1, 2, 3].forEach(i => {
        const dot  = document.getElementById(`step-dot-${i}`);
        const line = document.getElementById(`step-line-${i}`);
        if (!dot) return;
        dot.classList.toggle("active",    i === step);
        dot.classList.toggle("completed", i < step);
        if (line) line.classList.toggle("completed", i < step);
    });
}

/* ─── Validação ─────────────────────────────────────────────────────────── */
function validateStep(step) {
    const container = document.getElementById(`fields-step-${step}`);
    if (!container) return true;
    let valid = true;

    container.querySelectorAll("input:not([type='hidden']), select").forEach(el => {
        const invalid = el.required && !el.value.trim();
        el.classList.toggle("error", invalid);
        if (invalid) valid = false;
    });

    container.querySelectorAll(".option-group[data-required='true']").forEach(group => {
        const h = group.querySelector("input[type='hidden']");
        const invalid = !h?.value;
        group.classList.toggle("error", invalid);
        if (invalid) valid = false;
    });

    if (!valid) container.querySelector(".error")?.scrollIntoView({ behavior: "smooth", block: "center" });
    return valid;
}

/* ─── Coleta de dados ───────────────────────────────────────────────────── */
function saveStepData(step) {
    const container = document.getElementById(`fields-step-${step}`);
    if (!container) return;
    container.querySelectorAll("input, select").forEach(el => {
        if (!el.name) return;
        if (el.type === "checkbox") formData[el.name] = el.checked;
        else if (el.type !== "radio" || el.checked) formData[el.name] = el.value;
    });
}

/* ─── Captura parcial (etapa 1) ─────────────────────────────────────────── */
async function savePartialLead() {
    const name  = (formData.full_name || "").trim();
    const phone = (formData.phone || "").trim();
    if (!name || !phone) return;
    try {
        const res = await fetch(`${API_URL}/leads/partial`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                client_id:  queryParams.client_id,
                link_id:    queryParams.link_id    || null,
                session_id: sessionId              || queryParams.session_id || null,
                name, phone,
                utm_data: { utm_source: queryParams.utm_source, utm_medium: queryParams.utm_medium, utm_campaign: queryParams.utm_campaign },
            }),
        });
        if (res.ok) { const d = await res.json(); if (d.lead_id) partialLeadId = d.lead_id; }
    } catch (err) { console.warn("[Funila] Captura parcial falhou (não crítico):", err.message); }
}

/* ─── Submit final ──────────────────────────────────────────────────────── */
async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    const consentEl = document.getElementById("lgpd-consent");
    if (!consentEl?.checked) {
        consentEl?.closest(".checkbox-group")?.classList.add("error");
        consentEl?.closest(".form-group")?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }
    consentEl.closest(".checkbox-group")?.classList.remove("error");
    saveStepData(3);

    const btn = e.target.querySelector("button[type='submit']");
    setLoading(btn, true);

    try {
        const res = await fetch(`${API_URL}/leads`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                client_id:     queryParams.client_id,
                link_id:       queryParams.link_id    || null,
                session_id:    sessionId              || queryParams.session_id || null,
                form_data:     formData,
                consent_given: true,
                utm_data: { utm_source: queryParams.utm_source, utm_medium: queryParams.utm_medium, utm_campaign: queryParams.utm_campaign, utm_content: queryParams.utm_content, utm_term: queryParams.utm_term },
            }),
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
            trackEvent("form_submit", { metadata: { score: data.score } });
            showSuccess(data);
        } else { throw new Error(data.detail || "Erro ao processar"); }
    } catch (err) {
        console.error("[Funila] Erro no submit:", err);
        setLoading(btn, false);
        showToast("Erro ao enviar. Verifique sua conexão e tente novamente.");
    }
}

function showSuccess(data) {
    document.querySelectorAll(".form-step").forEach(el => el.classList.remove("active"));
    document.querySelector(".progress-container")?.style.setProperty("display", "none");
    document.getElementById("step-success")?.classList.add("active");
    currentStep = 4;
    const waBtn = document.getElementById("whatsapp-btn");
    if (waBtn && data.whatsapp_link) waBtn.href = data.whatsapp_link;
}

/* ─── Máscaras ──────────────────────────────────────────────────────────── */
function setupMasks() {
    document.querySelectorAll(".mask-phone").forEach(input => {
        input.addEventListener("input", e => {
            const d = e.target.value.replace(/\D/g, "").slice(0, 11);
            const m = d.match(/^(\d{0,2})(\d{0,5})(\d{0,4})$/) || [];
            e.target.value = !m[2] ? (m[1] || "") : `(${m[1]}) ${m[2]}${m[3] ? "-" + m[3] : ""}`;
        });
    });
    document.querySelectorAll(".mask-cpf").forEach(input => {
        input.addEventListener("input", e => {
            const d = e.target.value.replace(/\D/g, "").slice(0, 11);
            const m = d.match(/^(\d{0,3})(\d{0,3})(\d{0,3})(\d{0,2})$/) || [];
            e.target.value = !m[2] ? (m[1] || "") : !m[3] ? `${m[1]}.${m[2]}` : !m[4] ? `${m[1]}.${m[2]}.${m[3]}` : `${m[1]}.${m[2]}.${m[3]}-${m[4]}`;
        });
    });
}

/* ─── Rastreio de campos ────────────────────────────────────────────────── */
function setupFieldTracking() {
    document.querySelectorAll("input:not([type='hidden']), select").forEach(el => {
        if (!el.name) return;
        el.addEventListener("focus", () => { fieldTimers[el.name] = Date.now(); trackEvent("field_focus", { field_key: el.name }); });
        el.addEventListener("blur",  () => {
            if (fieldTimers[el.name]) {
                trackEvent("field_blur", { field_key: el.name, metadata: { time_ms: Date.now() - fieldTimers[el.name] } });
                delete fieldTimers[el.name];
            }
        });
        el.addEventListener("input", () => el.classList.remove("error"));
    });
}

/* ─── Utilidades de UI ───────────────────────────────────────────────────── */
function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    if (loading) { btn.dataset.orig = btn.innerHTML; btn.innerHTML = `<span class="spinner"></span>Enviando...`; }
    else btn.innerHTML = btn.dataset.orig || "Enviar";
}

function showFatalError(msg) {
    document.body.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;min-height:100vh;padding:32px;background:#0A0C10;font-family:'Sora',system-ui,sans-serif;"><div style="max-width:360px;background:#111318;border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:40px 32px;text-align:center;color:#F0F2F5;"><div style="width:44px;height:44px;border-radius:50%;background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.25);display:flex;align-items:center;justify-content:center;margin:0 auto 20px;color:#F87171;font-weight:700;font-size:18px;">!</div><p style="font-size:.9rem;color:#8A919E;line-height:1.6;">${msg}</p></div></div>`;
}

function showToast(msg) {
    document.querySelector(".toast")?.remove();
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add("toast-hide"), 3500);
    setTimeout(() => t.remove(), 4000);
}