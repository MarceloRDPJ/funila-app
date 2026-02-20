const KANBAN_COLUMNS = ['cold', 'warm', 'negotiation', 'converted', 'trash'];
const COLUMN_LABELS = {
    'cold': 'Frio / Incompleto',
    'warm': 'Morno',
    'negotiation': 'Em Negociação',
    'converted': 'Convertido',
    'trash': 'Descartado'
};

document.addEventListener("DOMContentLoaded", () => {
    // Override loadLeads to render Kanban
    // We keep existing loadLeads logic but change render function
    // Check if we are on leads page
    if (document.getElementById("kanban-board")) {
        // Initialize Kanban
    }
});

function renderKanbanBoard(leads) {
    const board = document.getElementById("kanban-board");
    board.innerHTML = ""; // Clear existing

    // Create columns
    const columns = {};
    KANBAN_COLUMNS.forEach(status => {
        const colDiv = document.createElement("div");
        colDiv.className = "kanban-column";
        colDiv.dataset.status = status;

        colDiv.innerHTML = `
            <div class="kanban-column-header">
                <span class="kanban-column-title">
                    <span style="width:8px;height:8px;border-radius:50%;background:${getStatusColor(status)}"></span>
                    ${COLUMN_LABELS[status]}
                </span>
                <span class="kanban-count" id="count-${status}">0</span>
            </div>
            <div class="kanban-cards-container" id="col-${status}">
                <!-- Cards go here -->
            </div>
        `;
        board.appendChild(colDiv);
        columns[status] = colDiv.querySelector(".kanban-cards-container");
    });

    // Distribute leads
    const counts = { cold: 0, warm: 0, negotiation: 0, converted: 0, trash: 0 };

    leads.forEach(lead => {
        let status = lead.status;
        if (!KANBAN_COLUMNS.includes(status)) {
            // Map unknown status to cold or warm?
            // If 'started', map to 'cold'
            if (status === 'started') status = 'cold';
            else if (status === 'hot') status = 'warm'; // Map hot to warm or create hot column?
            // Prompt said columns: cold, warm, negotiation, converted, trash.
            // But DB has 'hot'.
            // I should probably map 'hot' to 'warm' or add 'hot' column?
            // Prompt explicitly listed columns. I will add 'hot' column if needed or map it.
            // Let's assume 'hot' goes to 'warm' or I should add 'hot' column.
            // Wait, "Kanban horizontal com colunas: cold, warm, negotiation, converted, trash".
            // So 'hot' leads will be hidden or mapped.
            // I'll map 'hot' to 'warm' visually, but keep data 'hot'?
            // Or maybe 'warm' column includes 'hot'.
            if (status === 'hot') status = 'warm';
            else status = 'cold'; // Default fallback
        }

        counts[status]++;
        const card = createKanbanCard(lead);
        columns[status].appendChild(card);
    });

    // Update counts
    KANBAN_COLUMNS.forEach(s => {
        const el = document.getElementById(`count-${s}`);
        if (el) el.innerText = counts[s];
    });

    // Initialize Sortable for each column
    KANBAN_COLUMNS.forEach(status => {
        const el = document.getElementById(`col-${status}`);
        new Sortable(el, {
            group: 'kanban', // set both lists to same group
            animation: 150,
            ghostClass: 'kanban-ghost',
            delay: 100, // delay to prevent accidental drag on touch
            delayOnTouchOnly: true,
            onEnd: async function (evt) {
                const itemEl = evt.item;
                const newStatus = evt.to.parentElement.dataset.status;
                const oldStatus = evt.from.parentElement.dataset.status;
                const leadId = itemEl.dataset.id;

                if (newStatus === oldStatus) return;

                // Optimistic update
                // Update counter
                updateCount(oldStatus, -1);
                updateCount(newStatus, 1);

                try {
                    await updateLeadStatus(leadId, newStatus);
                    showToast(`Lead movido para ${COLUMN_LABELS[newStatus]}`, "success");

                    if (newStatus === 'converted') {
                        fireConfetti();
                    }
                } catch (error) {
                    // Revert
                    showToast("Erro ao mover lead", "error");
                    // Sortable doesn't easily revert via API, we might need to move DOM back manually
                    // or just reload. Reloading is safer for state consistency.
                    // But simpler: just append back to 'from'
                    evt.from.appendChild(itemEl);
                    updateCount(oldStatus, 1);
                    updateCount(newStatus, -1);
                }
            },
        });
    });
}

function createKanbanCard(lead) {
    const card = document.createElement("div");
    card.className = "kanban-card";
    card.dataset.id = lead.id;

    const score = (lead.internal_score || 0) + (lead.external_score || 0);
    const date = new Date(lead.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
    const phoneClean = lead.phone ? lead.phone.replace(/\D/g, "") : "";
    const waLink = phoneClean ? `https://wa.me/55${phoneClean}` : "#";
    const name = lead.name || "Sem Nome";

    // Check for "Etapa abandonada"
    let subtext = "";
    if (lead.status === 'started' || (lead.status === 'cold' && !lead.consent_given)) {
        subtext = `<span style="color:#F87171">Abandono</span>`;
    } else {
        subtext = `Score: ${score}`;
    }

    card.innerHTML = `
        <div class="kanban-card-header">
            <span class="kanban-card-title truncate" title="${name}">${name}</span>
            <span class="kanban-card-score">${score}</span>
        </div>
        <div class="kanban-card-body">
            ${subtext}
        </div>
        <div class="kanban-card-footer">
            <span class="kanban-date">${date}</span>
            <div style="display:flex;gap:8px">
                <a href="${waLink}" target="_blank" class="btn-whatsapp-mini" title="WhatsApp">
                    <i data-lucide="message-circle" style="width:14px"></i>
                </a>
                <button class="btn-whatsapp-mini" style="background:#333" onclick="openLeadDetails('${lead.id}')">
                    <i data-lucide="eye" style="width:14px"></i>
                </button>
            </div>
        </div>
    `;
    return card;
}

function updateCount(status, change) {
    const el = document.getElementById(`count-${status}`);
    if (el) {
        let val = parseInt(el.innerText) || 0;
        el.innerText = Math.max(0, val + change);
    }
}

function getStatusColor(status) {
    switch(status) {
        case 'cold': return '#60A5FA';
        case 'warm': return '#F59E0B';
        case 'negotiation': return '#3B82F6';
        case 'converted': return '#8B5CF6';
        case 'trash': return '#EF4444';
        default: return '#ccc';
    }
}

async function updateLeadStatus(leadId, newStatus) {
    const session = await Auth.checkAuth();
    if (!session) throw new Error("No session");

    const res = await fetch(`${Auth.API_URL}/leads/${leadId}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ status: newStatus })
    });

    if (!res.ok) throw new Error("API Error");
    return await res.json();
}

// Toast helper (reusing existing or creating new if needed, existing leads.html has toast container)
function showToast(msg, type="success") {
    const container = document.getElementById("toast-container");
    if (!container) return; // Should exist in leads.html

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i data-lucide="${type === 'success' ? 'check-circle' : 'alert-circle'}" class="toast-icon"></i>
        <span>${msg}</span>
    `;
    container.appendChild(toast);
    lucide.createIcons(); // Refresh icons

    setTimeout(() => {
        toast.style.animation = "slideOut 0.3s forwards"; // Add slideOut keyframes if not exists, or just remove
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Confetti
function fireConfetti() {
    const colors = ['#a864fd', '#29cdff', '#78ff44', '#ff718d', '#fdff6a'];
    for (let i = 0; i < 50; i++) {
        const conf = document.createElement('div');
        conf.className = 'confetti';
        conf.style.left = Math.random() * 100 + 'vw';
        conf.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        conf.style.animationDuration = (Math.random() * 2 + 1) + 's';
        document.body.appendChild(conf);
        setTimeout(() => conf.remove(), 3000);
    }
}
