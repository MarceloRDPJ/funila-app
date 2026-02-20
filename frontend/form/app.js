const API_URL = "https://funila-api.onrender.com";
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
    if (!queryParams.session_id) return; // Se não tem sessão, ignora (ou gera uma nova?)

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
        // Silencioso para não atrapalhar UX
        console.warn("Tracking error", e);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    // Rastreia início do formulário
    if (queryParams.session_id) {
        trackEvent("step_start", 1);
    }

    if (!queryParams.client_id) {
        document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:50px;'>Erro: Cliente não identificado.</h1>";
        return;
    }
    try {
        const res = await fetch(`${API_URL}/forms/config/${queryParams.client_id}`);
        if (!res.ok) throw new Error("Config não encontrada");
        clientConfig = await res.json();
        renderForm(clientConfig);
    } catch (e) {
        console.error(e);
        document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:50px;'>Erro ao carregar formulário.</h1>";
    }
    document.getElementById("lead-form").addEventListener("submit", handleSubmit);

    // Rastreia abandono (best-effort)
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden") {
            trackEvent("form_abandon", currentStep);
        }
    });
});

function renderForm(config) {
    document.getElementById("client-name").innerText = config.client_name;
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
    container.innerHTML = "";

    fields.sort((a, b) => a.order - b.order).forEach(field => {
        const group = document.createElement("div");
        group.className = "form-group";

        const label = document.createElement("label");
        label.innerText = field.label + (field.required ? " *" : "");
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

                // Tracking change
                radio.addEventListener("change", () => {
                    input.querySelectorAll(".radio-option").forEach(l => l.classList.remove("selected"));
                    radioLabel.classList.add("selected");
                    trackEvent("field_blur", currentStep, field.field_key); // Radio change is effectively a complete/blur
                });

                radioLabel.appendChild(radio);
                radioLabel.appendChild(document.createTextNode(opt));
                input.appendChild(radioLabel);
            });
        } else {
            input = document.createElement("input");
            input.type = "text"; input.name = field.field_key;
            if (field.required) input.required = true;
            input.placeholder = field.label;
            if (field.field_key === "phone") input.classList.add("mask-phone");
            if (field.field_key === "cpf")   input.classList.add("mask-cpf");
        }

        // Tracking events for standard inputs
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

    // Salvar parcial se for etapa 1
    if (step === 1) {
        partialSavePromise = savePartialLead();
    }

    if (step < 3) {
        document.getElementById(`step-${step}`).classList.remove("active");
        document.getElementById(`step-${step + 1}`).classList.add("active");
        document.getElementById(`step-dot-${step}`).style.backgroundColor = "var(--accent)";
        document.getElementById(`step-dot-${step + 1}`).classList.add("active");
        currentStep++;
        trackEvent("step_start", currentStep);
    }
};

window.prevStep = function(step) {
    if (step > 1) {
        document.getElementById(`step-${step}`).classList.remove("active");
        document.getElementById(`step-${step - 1}`).classList.add("active");
        currentStep--;
        trackEvent("step_start", currentStep); // Voltar também é iniciar a etapa
    }
};

function validateStep(step) {
    const container = document.getElementById(`fields-step-${step}`);
    let valid = true;
    container.querySelectorAll("input, select").forEach(input => {
        if (!input.checkValidity()) { input.reportValidity(); valid = false; }
    });
    return valid;
}

function saveStepData(step) {
    const container = document.getElementById(`fields-step-${step}`);
    container.querySelectorAll("input, select").forEach(input => {
        if (input.type === "radio") {
            if (input.checked) formData[input.name] = input.value;
        } else {
            formData[input.name] = input.value;
        }
    });
}

async function savePartialLead() {
    // Dados mínimos para partial save
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
            leadId = data.lead_id; // Armazena ID para uso no submit final
            console.log("Lead parcial salvo:", leadId);
        }
    } catch (e) {
        console.error("Erro ao salvar lead parcial:", e);
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    const consent = document.getElementById("lgpd-consent");
    if (!consent.checked) {
        alert("Você precisa aceitar a Política de Privacidade para continuar.");
        return;
    }

    saveStepData(3);

    const btn = e.target.querySelector("button[type='submit']");
    btn.disabled = true;
    btn.innerText = "Enviando...";

    // Aguarda salvamento parcial se estiver pendente
    if (partialSavePromise) {
        try { await partialSavePromise; } catch(e) {}
    }

    try {
        const payload = {
            client_id:     queryParams.client_id,
            link_id:       queryParams.link_id,
            lead_id:       leadId, // Envia ID se existir
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
            btn.innerText = "Enviar e falar com o corretor";
        }
    } catch (err) {
        console.error(err);
        alert("Erro de conexão. Tente novamente.");
        btn.disabled = false;
        btn.innerText = "Enviar e falar com o corretor";
    }
}

function showSuccess(data) {
    document.querySelectorAll(".form-step").forEach(el => el.classList.remove("active"));
    document.querySelector(".progress-container").style.display = "none";
    const successDiv = document.getElementById("step-success");
    successDiv.classList.add("active");
    successDiv.style.display = "flex";
    document.getElementById("whatsapp-btn").href = data.whatsapp_link;
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
