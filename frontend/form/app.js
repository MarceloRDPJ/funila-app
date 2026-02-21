const API_URL = "https://funila-app.onrender.com";
let currentStep = 1;
let clientConfig = null;
let formData = {};
let leadId = null;
let saveTimeout = null;

function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        client_id:    params.get("c")            || params.get("client_id"),
        link_id:      params.get("l")            || params.get("link_id"),
        session_id:   params.get("sid")          || params.get("session_id"),
        utm_source:   params.get("utm_source")   || "",
        utm_medium:   params.get("utm_medium")   || "",
        utm_campaign: params.get("utm_campaign") || "",
        utm_content:  params.get("utm_content")  || "",
        utm_term:     params.get("utm_term")     || "",
    };
}

const queryParams = getQueryParams();

// Geração de ID de Sessão
function getSessionId() {
    let sid = sessionStorage.getItem("funila_session_id");
    if (!sid) {
        sid = crypto.randomUUID();
        sessionStorage.setItem("funila_session_id", sid);
    }
    return sid;
}
const sessionId = queryParams.session_id || getSessionId();

// Rastreamento
async function trackEvent(eventType, step = null, fieldKey = null, metadata = {}) {
    const payload = {
        session_id:  sessionId,
        link_id:     queryParams.link_id,
        event_type:  eventType,
        step:        step,
        field_key:   fieldKey,
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

// Salvamento Automático / Telemetria
function saveProgress(stepName) {
    if (saveTimeout) clearTimeout(saveTimeout);

    saveTimeout = setTimeout(async () => {
        // Coleta dados atuais
        const payload = {
            client_id:    queryParams.client_id,
            link_id:      queryParams.link_id,
            lead_id:      leadId,
            name:         formData["full_name"],
            phone:        formData["phone"],
            last_step:    stepName,
            utm_data: {
                utm_source:   queryParams.utm_source,
                utm_medium:   queryParams.utm_medium,
                utm_campaign: queryParams.utm_campaign,
            }
        };

        // Salva apenas se tivermos pelo menos nome ou telefone para identificar
        if(!payload.name && !payload.phone) return;

        try {
            const res = await fetch(`${API_URL}/leads/partial`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.status === "success" && data.lead_id) {
                leadId = data.lead_id;
            }
        } catch (e) {
            console.error("Autosave error", e);
        }
    }, 1000); // 1s debounce
}

function showLoading() {
    const header = document.querySelector(".header");
    if (header) {
        header.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;gap:10px;padding:20px">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3B6EF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
                <p style="color:var(--text-secondary);font-size:0.9rem">Carregando formulário...</p>
            </div>`;
    }
}

function showError(msg) {
    document.querySelector(".app-container").innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:80vh;text-align:center;padding:20px;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:16px"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <h2 style="font-size:1.2rem;margin-bottom:8px;color:var(--text-primary)">Algo deu errado</h2>
            <p style="color:var(--text-secondary);font-size:0.9rem">${msg}</p>
            <button onclick="window.location.reload()" style="margin-top:24px;padding:12px 24px;background:var(--accent);border:none;border-radius:12px;color:white;cursor:pointer;font-weight:600">Tentar novamente</button>
        </div>
    `;
}

// Implementação de Toast
function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const icon = type === "success"
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;

    toast.innerHTML = `${icon} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-10px)";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

document.addEventListener("DOMContentLoaded", async () => {
    if (!document.getElementById("spinner-style")) {
        const style = document.createElement("style");
        style.id = "spinner-style";
        style.textContent = `
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .animate-spin { animation: spin 1s linear infinite; }
        `;
        document.head.appendChild(style);
    }

    trackEvent("step_start", 1);

    if (!queryParams.client_id) {
        showError("Link inválido ou cliente não identificado.");
        return;
    }

    showLoading();

    try {
        const res = await fetch(`${API_URL}/forms/config/${queryParams.client_id}`);
        if (!res.ok) throw new Error("Config não encontrada");
        clientConfig = await res.json();
        renderForm(clientConfig);
    } catch (e) {
        console.error(e);
        showError("Não foi possível carregar o formulário. Verifique sua conexão.");
    }

    const form = document.getElementById("lead-form");
    if (form) form.addEventListener("submit", handleSubmit);

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            trackEvent("form_abandon", currentStep);
        }
    });
});

function renderForm(config) {
    // White-Label Application
    if (config.brand_primary_color) {
        document.documentElement.style.setProperty('--accent', config.brand_primary_color);
    }

    // Logo replacement (assuming there is an img with id 'form-logo' in index.html, or we inject it)
    // The current index.html layout needs to be checked or we robustly look for it.
    const logoEl = document.getElementById("form-logo");
    if (logoEl && config.brand_logo_url) {
        logoEl.src = config.brand_logo_url;
    }

    // Header content is already static in HTML, no need to overwrite it and destroy the logo.
    // const header = document.querySelector(".header");
    // header.innerHTML = ...

    document.title = `${config.client_name} - Qualificação`;

    const step1Fields = config.fields.filter(f => ["full_name", "phone", "email"].includes(f.field_key));
    const step3Fields = config.fields.filter(f => ["income_range", "tried_financing", "cpf"].includes(f.field_key));
    const step2Fields = config.fields.filter(f => !step1Fields.includes(f) && !step3Fields.includes(f));

    renderFieldsToContainer(step1Fields, "fields-step-1");
    renderFieldsToContainer(step2Fields, "fields-step-2");
    renderFieldsToContainer(step3Fields, "fields-step-3");
    setupMasks();
}

function renderFieldsToContainer(fields, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    fields.sort((a, b) => a.order - b.order).forEach(field => {
        const group = document.createElement("div");
        group.className = "form-group";

        const label = document.createElement("label");
        label.innerText = (field.label_custom || field.label) + (field.required ? " *" : "");
        group.appendChild(label);

        let input;

        if (field.type === "select") {
            input = document.createElement("select");
            input.name = field.field_key;
            if (field.required) input.required = true;
            const defaultOpt = document.createElement("option");
            defaultOpt.value = ""; defaultOpt.text = "Selecione...";
            input.appendChild(defaultOpt);
            let opts = field.options;
            if (typeof opts === "string") opts = JSON.parse(opts);
            if (opts) opts.forEach(opt => {
                const o = document.createElement("option");
                o.value = opt; o.text = opt;
                input.appendChild(o);
            });
            input.addEventListener("change", () => {
                formData[field.field_key] = input.value;
                saveProgress(field.field_key);
            });
        } else if (field.type === "radio") {
            input = document.createElement("div");
            input.className = "radio-group";
            let opts = field.options;
            if (typeof opts === "string") opts = JSON.parse(opts);
            if (opts) opts.forEach(opt => {
                const radioLabel = document.createElement("label");
                radioLabel.className = "radio-option";
                const radio = document.createElement("input");
                radio.type = "radio"; radio.name = field.field_key; radio.value = opt;
                if (field.required) radio.required = true;

                radioLabel.addEventListener("click", (e) => {
                    if(e.target === radio) return;
                    radio.checked = true;
                    input.querySelectorAll(".radio-option").forEach(l => l.classList.remove("selected"));
                    radioLabel.classList.add("selected");

                    formData[field.field_key] = opt;
                    trackEvent("field_blur", currentStep, field.field_key);
                    saveProgress(field.field_key);
                });

                radioLabel.appendChild(radio);
                radioLabel.appendChild(document.createTextNode(opt));
                input.appendChild(radioLabel);
            });
        } else {
            input = document.createElement("input");
            input.type = "text"; input.name = field.field_key;
            if (field.required) input.required = true;
            input.placeholder = field.label_custom || field.label;
            if (field.field_key === "phone") input.classList.add("mask-phone");
            if (field.field_key === "cpf")   input.classList.add("mask-cpf");

            input.addEventListener("blur", () => {
                formData[field.field_key] = input.value;
                saveProgress(field.field_key);
                trackEvent("field_blur", currentStep, field.field_key);
            });
        }

        if (field.type !== "radio") {
            input.addEventListener("focus", () => trackEvent("field_focus", currentStep, field.field_key));
        }

        group.appendChild(input);
        container.appendChild(group);
    });
}

window.nextStep = async function(step) {
    if (!validateStep(step)) return;
    saveStepData(step);

    // Telemetria: Etapa Completa
    trackEvent("step_complete", step);
    saveProgress(`step_${step}_complete`);

    const currentStepEl = document.getElementById(`step-${step}`);
    const nextStepEl = document.getElementById(`step-${step + 1}`);

    if (nextStepEl) {
        currentStepEl.classList.remove("active");
        nextStepEl.classList.add("active");

        const currentDot = document.getElementById(`step-dot-${step}`);
        const nextDot = document.getElementById(`step-dot-${step + 1}`);
        if (currentDot) currentDot.style.background = "var(--accent)";
        if (nextDot) nextDot.classList.add("active");

        currentStep++;
        trackEvent("step_start", currentStep);
    }
};

window.prevStep = function(step) {
    if (step > 1) {
        document.getElementById(`step-${step}`).classList.remove("active");
        document.getElementById(`step-${step - 1}`).classList.add("active");
        currentStep--;
        trackEvent("step_start", currentStep);
    }
};

function validateStep(step) {
    const container = document.getElementById(`fields-step-${step}`);
    if (!container) return true;
    let valid = true;

    const radioGroups = container.querySelectorAll(".radio-group");
    radioGroups.forEach(group => {
        const inputs = group.querySelectorAll("input[type='radio']");
        if(inputs.length > 0 && inputs[0].required) {
            const checked = Array.from(inputs).some(i => i.checked);
            if(!checked) {
                valid = false;
                showToast("Por favor, selecione uma opção.", "error");
            }
        }
    });

    if(!valid) return false;

    container.querySelectorAll("input:not([type='radio']), select").forEach(input => {
        if (!input.checkValidity()) {
            input.reportValidity();
            valid = false;
            input.style.borderColor = "#EF4444";
            setTimeout(() => input.style.borderColor = "", 2000);
        }
    });
    return valid;
}

function saveStepData(step) {
    const container = document.getElementById(`fields-step-${step}`);
    if (!container) return;
    container.querySelectorAll("input, select").forEach(input => {
        if (input.type === "radio") {
            if (input.checked) formData[input.name] = input.value;
        } else {
            formData[input.name] = input.value;
        }
    });
}

async function validateCPF(cpf) {
    const digits = cpf.replace(/\D/g, "");
    if (!digits || digits.length !== 11) return true; // optional field, skip if empty
    // Basic digit validation
    if (/^(\d)\1+$/.test(digits)) return false;
    // BrasilAPI validation
    try {
        const r = await fetch(`https://brasilapi.com.br/api/cpf/v1/${digits}`, { signal: AbortSignal.timeout(5000) });
        return r.ok;
    } catch {
        return true; // network failure → allow submit
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    const consent = document.getElementById("lgpd-consent");
    if (!consent || !consent.checked) {
        showToast("Você precisa aceitar a Política de Privacidade.", "error");
        return;
    }

    // Validate CPF via BrasilAPI if provided
    const cpfInput = document.querySelector(".mask-cpf");
    if (cpfInput && cpfInput.value.trim()) {
        const btn0 = e.target.querySelector("button[type='submit']");
        if (btn0) { btn0.disabled = true; btn0.innerHTML = "Validando CPF..."; }
        const cpfOk = await validateCPF(cpfInput.value);
        if (!cpfOk) {
            showToast("CPF inválido. Verifique o número ou deixe em branco.", "error");
            if (btn0) { btn0.disabled = false; btn0.innerHTML = "Enviar e falar com o corretor"; }
            return;
        }
        if (btn0) btn0.disabled = false;
    }

    saveStepData(3);

    const btn = e.target.querySelector("button[type='submit']");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg> Enviando...`;

    // Garante estado final salvo antes do envio
    if (saveTimeout) clearTimeout(saveTimeout);

    try {
        const payload = {
            client_id:     queryParams.client_id,
            link_id:       queryParams.link_id,
            lead_id:       leadId,
            form_data:     formData,
            consent_given: true,
            utm_data: {
                utm_source:   queryParams.utm_source,
                utm_medium:   queryParams.utm_medium,
                utm_campaign: queryParams.utm_campaign,
                utm_content:  queryParams.utm_content,
                utm_term:     queryParams.utm_term,
            }
        };

        const res = await fetch(`${API_URL}/leads`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.status === "success") {
            trackEvent("form_submit");
            handleSuccessAction(data);
        } else {
            showToast("Erro ao enviar. Tente novamente.", "error");
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (err) {
        console.error(err);
        showToast("Erro de conexão. Tente novamente.", "error");
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function handleSuccessAction(data) {
    // Verifica config para Ação (Redirecionar vs Mensagem)
    // Assumindo que config tem campo 'finish_action'. Se não presente, padrão redirecionar (comportamento legado)
    // Precisamos recarregar config ou armazenar globalmente. Armazenado em clientConfig.

    const action = clientConfig.finish_action || "redirect";

    if (action === "message") {
        document.querySelectorAll(".form-step").forEach(el => el.classList.remove("active"));
        const progress = document.querySelector(".progress-container");
        if (progress) progress.style.display = "none";

        const successDiv = document.getElementById("step-success");
        if (successDiv) {
            successDiv.classList.add("active");
            successDiv.style.display = "block";
        }

        // Esconde botão do WhatsApp se estiver mostrando apenas mensagem de sucesso? Ou mantém como opção?
        // Requisito diz "Mostrar card de sucesso premium". Geralmente implica sem auto-redirecionamento.
        // Podemos manter o botão manual.
        const waBtn = document.getElementById("whatsapp-btn");
        if (waBtn && data.whatsapp_link) waBtn.href = data.whatsapp_link;

    } else {
        // Redirecionamento
        if (data.whatsapp_link) {
            window.location.href = data.whatsapp_link;
        } else {
            showToast("Sucesso! Entraremos em contato.", "success");
        }
    }
}

function setupMasks() {
    document.querySelectorAll(".mask-phone").forEach(input => {
        input.addEventListener("input", e => {
            let x = e.target.value.replace(/\D/g, "").match(/(\d{0,2})(\d{0,5})(\d{0,4})/);
            e.target.value = !x[2] ? x[1] : "(" + x[1] + ") " + x[2] + (x[3] ? "-" + x[3] : "");
        });
    });
    document.querySelectorAll(".mask-cpf").forEach(input => {
        input.addEventListener("input", e => {
            let x = e.target.value.replace(/\D/g, "").match(/(\d{0,3})(\d{0,3})(\d{0,3})(\d{0,2})/);
            e.target.value = !x[2] ? x[1] : x[1] + "." + x[2] + "." + x[3] + (x[4] ? "-" + x[4] : "");
        });
    });
}
