const API_URL = "http://localhost:8000"; // Change for prod
let currentStep = 1;
let clientConfig = null;
let formData = {};

// Helper: Get URL Params
function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        client_id: params.get("c") || params.get("client_id"),
        link_id: params.get("l") || params.get("link_id"),
        utm_source: params.get("utm_source"),
        utm_medium: params.get("utm_medium"),
        utm_campaign: params.get("utm_campaign"),
        utm_content: params.get("utm_content"),
        utm_term: params.get("utm_term")
    };
}

const queryParams = getQueryParams();

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    if (!queryParams.client_id) {
        document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:50px;'>Erro: Cliente não identificado.</h1>";
        return;
    }

    try {
        const response = await fetch(`${API_URL}/forms/config/${queryParams.client_id}`);
        if (!response.ok) throw new Error("Config not found");

        clientConfig = await response.json();
        renderForm(clientConfig);
    } catch (e) {
        console.error(e);
        document.body.innerHTML = "<h1 style='color:white;text-align:center;margin-top:50px;'>Erro ao carregar formulário.</h1>";
    }

    // Attach submit handler
    document.getElementById("lead-form").addEventListener("submit", handleSubmit);
});

// Render Fields
function renderForm(config) {
    document.getElementById("client-name").innerText = config.client_name;
    document.title = `${config.client_name} - Qualificação`;

    // Categorize fields into steps (Simple mapping logic)
    // Step 1: full_name, phone
    // Step 2: has_clt, clt_years, profession, etc.
    // Step 3: income_range, tried_financing, cpf

    const step1Fields = config.fields.filter(f => ['full_name', 'phone', 'email'].includes(f.field_key));
    const step3Fields = config.fields.filter(f => ['income_range', 'tried_financing', 'cpf'].includes(f.field_key));
    const step2Fields = config.fields.filter(f => !step1Fields.includes(f) && !step3Fields.includes(f));

    renderFieldsToContainer(step1Fields, "fields-step-1");
    renderFieldsToContainer(step2Fields, "fields-step-2");
    renderFieldsToContainer(step3Fields, "fields-step-3");

    // Masking
    setupMasks();
}

function renderFieldsToContainer(fields, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";

    fields.sort((a, b) => a.order - b.order).forEach(field => {
        const group = document.createElement("div");
        group.className = "form-group";

        const label = document.createElement("label");
        label.innerText = field.label;
        if (field.required) label.innerText += " *";
        group.appendChild(label);

        let input;

        if (field.type === "select") {
            input = document.createElement("select");
            input.name = field.field_key;
            if (field.required) input.required = true;

            const defaultOpt = document.createElement("option");
            defaultOpt.value = "";
            defaultOpt.text = "Selecione...";
            input.appendChild(defaultOpt);

            if (field.options) {
                // Parse if string, or use directly if array (API returns JSON/Array)
                let opts = field.options;
                if (typeof opts === 'string') opts = JSON.parse(opts);

                opts.forEach(opt => {
                    const o = document.createElement("option");
                    o.value = opt;
                    o.text = opt;
                    input.appendChild(o);
                });
            }
        } else if (field.type === "radio") {
            // Render as cards
            input = document.createElement("div");
            input.className = "radio-group";

            let opts = field.options;
            if (typeof opts === 'string') opts = JSON.parse(opts);

            opts.forEach(opt => {
                const radioLabel = document.createElement("label");
                radioLabel.className = "radio-option";

                const radio = document.createElement("input");
                radio.type = "radio";
                radio.name = field.field_key;
                radio.value = opt;
                if (field.required) radio.required = true;

                radio.addEventListener("change", () => {
                    // Highlight logic
                    input.querySelectorAll(".radio-option").forEach(l => l.classList.remove("selected"));
                    radioLabel.classList.add("selected");
                });

                radioLabel.appendChild(radio);
                radioLabel.appendChild(document.createTextNode(opt));
                input.appendChild(radioLabel);
            });

        } else {
            // Text, email, phone, cpf
            input = document.createElement("input");
            input.type = field.type === "number" ? "tel" : "text"; // tel for mobile keyboard
            input.name = field.field_key;
            if (field.required) input.required = true;
            input.placeholder = field.label; // Use label as placeholder too

            if (field.field_key === "phone") input.classList.add("mask-phone");
            if (field.field_key === "cpf") input.classList.add("mask-cpf");
        }

        group.appendChild(input);
        container.appendChild(group);
    });
}

// Navigation
window.nextStep = function(step) {
    if (!validateStep(step)) return;

    // Capture data from this step
    saveStepData(step);

    if (step < 3) {
        document.getElementById(`step-${step}`).classList.remove("active");
        document.getElementById(`step-${step + 1}`).classList.add("active");

        // Update dots
        document.getElementById(`step-dot-${step}`).classList.remove("active"); // keep previous active? Usually accumulative.
        document.getElementById(`step-dot-${step + 1}`).classList.add("active");
        document.getElementById(`step-dot-${step}`).style.backgroundColor = "var(--accent)"; // Mark completed

        currentStep++;
    }
};

window.prevStep = function(step) {
    if (step > 1) {
        document.getElementById(`step-${step}`).classList.remove("active");
        document.getElementById(`step-${step - 1}`).classList.add("active");
        currentStep--;
    }
};

function validateStep(step) {
    const container = document.getElementById(`fields-step-${step}`);
    const inputs = container.querySelectorAll("input, select");
    let valid = true;

    inputs.forEach(input => {
        if (!input.checkValidity()) {
            input.reportValidity();
            valid = false;
        }
    });

    return valid;
}

function saveStepData(step) {
    const container = document.getElementById(`fields-step-${step}`);
    const inputs = container.querySelectorAll("input, select");

    inputs.forEach(input => {
        if (input.type === "radio") {
            if (input.checked) formData[input.name] = input.value;
        } else {
            formData[input.name] = input.value;
        }
    });
}

async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    // LGPD check
    if (!document.getElementById("lgpd-consent").checked) {
        alert("Você precisa aceitar os termos.");
        return;
    }

    saveStepData(3);

    // Show Loading or disable button
    const btn = e.target.querySelector("button[type='submit']");
    btn.disabled = true;
    btn.innerText = "Enviando...";

    try {
        const payload = {
            client_id: queryParams.client_id,
            link_id: queryParams.link_id,
            form_data: formData,
            utm_data: {
                utm_source: queryParams.utm_source,
                utm_campaign: queryParams.utm_campaign,
                // ... others
            }
        };

        const res = await fetch(`${API_URL}/leads`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (data.status === "success") {
            showSuccess(data);
        } else {
            alert("Erro ao enviar. Tente novamente.");
            btn.disabled = false;
        }
    } catch (err) {
        console.error(err);
        alert("Erro de conexão.");
        btn.disabled = false;
    }
}

function showSuccess(data) {
    // Hide form steps
    document.querySelectorAll(".form-step").forEach(el => el.classList.remove("active"));
    document.querySelector(".progress-container").style.display = "none";

    // Show success
    const successDiv = document.getElementById("step-success");
    successDiv.classList.add("active");
    successDiv.style.display = "flex";

    // Update WhatsApp Link
    const waBtn = document.getElementById("whatsapp-btn");
    waBtn.href = data.whatsapp_link;
}

// Simple Masks
function setupMasks() {
    const phoneInputs = document.querySelectorAll(".mask-phone");
    phoneInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let x = e.target.value.replace(/\D/g, '').match(/(\d{0,2})(\d{0,5})(\d{0,4})/);
            e.target.value = !x[2] ? x[1] : '(' + x[1] + ') ' + x[2] + (x[3] ? '-' + x[3] : '');
        });
    });

    const cpfInputs = document.querySelectorAll(".mask-cpf");
    cpfInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let x = e.target.value.replace(/\D/g, '').match(/(\d{0,3})(\d{0,3})(\d{0,3})(\d{0,2})/);
            e.target.value = !x[2] ? x[1] : x[1] + '.' + x[2] + '.' + x[3] + (x[4] ? '-' + x[4] : '');
        });
    });
}
