const API_URL = "https://funila-app.onrender.com";
let currentStep = 1;
let clientConfig = null;
let formData = {};
let leadId = null;
let partialSavePromise = null;

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

// Rastreamento de eventos
async function trackEvent(eventType, step = null, fieldKey = null, metadata = {}) {
    if (!queryParams.session_id) return;

    const payload = {
        session_id:  queryParams.session_id,
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

function showLoading() {
    const header = document.querySelector(".header");
    if (header) {
        header.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;gap:10px;padding:20px">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3B6EF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>
                <p style="color:var(--text-muted);font-size:0.9rem">Carregando formulário...</p>
            </div>`;
    }
}

function showError(msg) {
    document.querySelector(".app-container").innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;text-align:center;padding:20px;color:white">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:16px"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <h2 style="font-size:1.2rem;margin-bottom:8px">Algo deu errado</h2>
            <p style="color:#9CA3AF;font-size:0.9rem">${msg}</p>
            <button onclick="window.location.reload()" style="margin-top:20px;padding:10px 20px;background:#3B6EF8;border:none;border-radius:6px;color:white;cursor:pointer">Tentar novamente</button>
        </div>
    `;
}

document.addEventListener("DOMContentLoaded", async () => {
    // Inject styles for spinner if not present
    if (!document.getElementById("spinner-style")) {
        const style = document.createElement("style");
        style.id = "spinner-style";
        style.textContent = `
            @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            .animate-spin { animation: spin 1s linear infinite; }
        `;
        document.head.appendChild(style);
    }

    if (queryParams.session_id) {
        trackEvent("step_start", 1);
    }

    if (!queryParams.client_id) {
        showError("Cliente não identificado.");
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
    // Restaurar header
    const header = document.querySelector(".header");
    header.innerHTML = `
        <h1 id="client-name" class="client-name">${config.client_name}</h1>
        <p class="headline">Responda rápido para agilizar seu atendimento</p>
    `;

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

                radio.addEventListener("change", () => {
                    input.querySelectorAll(".radio-option").forEach(l => l.classList.remove("selected"));
                    radioLabel.classList.add("selected");
                    trackEvent("field_blur", currentStep, field.field_key);
                });

                radioLabel.appendChild(radio);
                radioLabel.appendChild(document.createTextNode(opt));
                input.appendChild(radioLabel);
            });
        } else {
            input = document.createElement("input");
            input.type = "text"; input.name = field.field_key;
            if (field.required) input.required = true;
            input.placeholder = field.label_custom || field.label; // Use custom label as placeholder too if desired
            if (field.field_key === "phone") input.classList.add("mask-phone");
            if (field.field_key === "cpf")   input.classList.add("mask-cpf");
        }

        if (field.type !== "radio") {
            input.addEventListener("focus", () => trackEvent("field_focus", currentStep, field.field_key));
            input.addEventListener("blur", () => trackEvent("field_blur", currentStep, field.field_key));
        }

        group.appendChild(input);
        container.appendChild(group);
    });
}

window.nextStep = async function(step) {
    if (!validateStep(step)) return;
    saveStepData(step);

    trackEvent("step_complete", step);

    if (step === 1) {
        partialSavePromise = savePartialLead();
    }

    const currentStepEl = document.getElementById(`step-${step}`);
    const nextStepEl = document.getElementById(`step-${step + 1}`);

    if (nextStepEl) {
        currentStepEl.classList.remove("active");
        nextStepEl.classList.add("active");

        const currentDot = document.getElementById(`step-dot-${step}`);
        const nextDot = document.getElementById(`step-dot-${step + 1}`);
        if (currentDot) currentDot.style.backgroundColor = "var(--accent)";
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
    container.querySelectorAll("input, select").forEach(input => {
        if (!input.checkValidity()) { input.reportValidity(); valid = false; }
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

async function savePartialLead() {
    const payload = {
        client_id:    queryParams.client_id,
        link_id:      queryParams.link_id,
        name:         formData["full_name"],
        phone:        formData["phone"],
        utm_data: {
            utm_source:   queryParams.utm_source,
            utm_medium:   queryParams.utm_medium,
            utm_campaign: queryParams.utm_campaign,
        }
    };

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
        console.error("Erro ao salvar lead parcial:", e);
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    const consent = document.getElementById("lgpd-consent");
    if (!consent || !consent.checked) {
        alert("Você precisa aceitar a Política de Privacidade para continuar.");
        return;
    }

    saveStepData(3);

    const btn = e.target.querySelector("button[type='submit']");
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="animate-spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg> Enviando...`;

    if (partialSavePromise) {
        try { await partialSavePromise; } catch(e) {}
    }

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
            showSuccess(data);
        } else {
            alert("Erro ao enviar. Tente novamente.");
            btn.disabled = false;
            btn.innerText = originalText;
        }
    } catch (err) {
        console.error(err);
        alert("Erro de conexão. Tente novamente.");
        btn.disabled = false;
        btn.innerText = originalText;
    }
}

function showSuccess(data) {
    document.querySelectorAll(".form-step").forEach(el => el.classList.remove("active"));
    const progress = document.querySelector(".progress-container");
    if (progress) progress.style.display = "none";

    const successDiv = document.getElementById("step-success");
    if (successDiv) {
        successDiv.classList.add("active");
        successDiv.style.display = "flex";
    }

    const waBtn = document.getElementById("whatsapp-btn");
    if (waBtn && data.whatsapp_link) waBtn.href = data.whatsapp_link;
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
