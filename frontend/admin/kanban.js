const KANBAN_COLUMNS = ['hot', 'warm', 'cold', 'abandoned', 'negotiation', 'converted', 'trash'];
const COLUMN_LABELS = {
    'hot': 'Quentes',
    'warm': 'Mornos',
    'cold': 'Frios',
    'abandoned': 'Abandonados',
    'negotiation': 'Negociação',
    'converted': 'Convertidos',
    'trash': 'Lixo'
};

const STATUS_COLORS = {
    'hot': 'var(--hot)',
    'warm': 'var(--warm)',
    'cold': 'var(--cold)',
    'abandoned': 'var(--dead)',
    'negotiation': '#818CF8',
    'converted': 'var(--purple)',
    'trash': '#4B5563'
};

function renderKanbanBoard(leads) {
    const board = document.getElementById("kanban-board");
    if (!board) return;
    board.innerHTML = "";

    // Cria as colunas
    const columns = {};
    KANBAN_COLUMNS.forEach(status => {
        const colDiv = document.createElement("div");
        colDiv.className = "kanban-column";
        colDiv.dataset.status = status;

        colDiv.innerHTML = `
            <div class="kanban-column-header">
                <span class="kanban-column-title">
                    <span style="width:6px;height:6px;border-radius:50%;background:${STATUS_COLORS[status] || '#ccc'}"></span>
                    ${COLUMN_LABELS[status]}
                </span>
                <span class="kanban-count" id="count-${status}">0</span>
            </div>
            <div class="kanban-cards-container" id="col-${status}">
            </div>
        `;
        board.appendChild(colDiv);
        columns[status] = colDiv.querySelector(".kanban-cards-container");
    });

    // Inicializa contadores
    const counts = {};
    KANBAN_COLUMNS.forEach(s => counts[s] = 0);

    // Distribui os leads
    leads.forEach(lead => {
        let status = lead.status;

        // Mapeamento de Abandono (Sprint 1.7)
        if (status === 'cold' && !lead.consent_given && lead.name) {
            status = 'abandoned';
        }

        // Lógica de Mapeamento
        if (!KANBAN_COLUMNS.includes(status)) {
            if (status === 'started') status = 'abandoned';
            else status = 'cold'; // Fallback
        }

        if (counts[status] !== undefined) {
            counts[status]++;
            const card = createKanbanCard(lead);
            columns[status].appendChild(card);
        }
    });

    // Atualiza contadores na UI
    KANBAN_COLUMNS.forEach(s => {
        const el = document.getElementById(`count-${s}`);
        if (el) el.innerText = counts[s];
    });

    // Inicializa SortableJS
    KANBAN_COLUMNS.forEach(status => {
        const el = document.getElementById(`col-${status}`);
        new Sortable(el, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'kanban-ghost',
            delay: 100,
            delayOnTouchOnly: true,
            onEnd: async function (evt) {
                const itemEl = evt.item;
                const newStatus = evt.to.parentElement.dataset.status;
                const oldStatus = evt.from.parentElement.dataset.status;
                const leadId = itemEl.dataset.id;

                if (newStatus === oldStatus) return;

                // Atualização Otimista
                updateCount(oldStatus, -1);
                updateCount(newStatus, 1);

                try {
                    await updateLeadStatus(leadId, newStatus);
                    showToast(`Movido para ${COLUMN_LABELS[newStatus]}`, "success");

                    if (newStatus === 'converted') {
                        fireConfetti();
                    }
                } catch (error) {
                    showToast("Erro ao mover lead", "error");
                    evt.from.appendChild(itemEl); // Reverter
                    updateCount(oldStatus, 1);
                    updateCount(newStatus, -1);
                }
            },
        });
    });

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function createKanbanCard(lead) {
    const card = document.createElement("div");
    card.className = "kanban-card";
    card.dataset.id = lead.id;

    const internalScore = lead.internal_score || 0;
    const serasaScore = lead.serasa_score || null;
    const scoreLabel = serasaScore
        ? `${internalScore} | Serasa: ${serasaScore}`
        : String(internalScore);

    const date = timeAgo(lead.created_at);
    const phoneClean = lead.phone ? lead.phone.replace(/\D/g, "") : "";
    const waLink = phoneClean ? `https://wa.me/55${phoneClean}` : "#";
    const name = lead.name || "Sem Nome";

    // Determina a classe do score
    let scoreClass = 'score-cold';
    if(internalScore >= 70) scoreClass = 'score-hot';
    else if(internalScore >= 40) scoreClass = 'score-warm';

    const stepLabel = lead.step_reached ? `Etapa ${lead.step_reached}/3` : "";
    const deviceIcon = lead.device_type === 'mobile' ? '📱' : '💻';
    const deviceLabel = lead.device_type || '';

    card.innerHTML = `
        <div class="kanban-card-header">
            <span class="kanban-card-title" title="${name}">${name}</span>
            <span class="score-badge ${scoreClass}">${scoreLabel}</span>
        </div>
        <div class="kanban-card-body">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                 <span style="font-size:0.65rem;color:var(--text-40)">
                    ${deviceIcon} ${deviceLabel}
                 </span>
                 <span style="font-size:0.65rem;color:var(--text-40)">${stepLabel}</span>
            </div>
            ${lead.utm_content ? `<div style="font-size:0.65rem;color:var(--text-40);background:var(--layer-2);padding:2px 4px;border-radius:4px;display:inline-block">📢 ${lead.utm_content}</div>` : ''}
        </div>
        <div class="kanban-card-footer">
            <span class="kanban-date">${date}</span>
            <div style="display:flex;gap:4px">
                <a href="${waLink}" target="_blank" class="lead-action-btn" onclick="event.stopPropagation();" title="WhatsApp">
                    <i data-lucide="message-circle" style="width:12px"></i>
                </a>
                <button class="lead-action-btn" onclick="openLeadDetails('${lead.id}'); event.stopPropagation();">
                    <i data-lucide="eye" style="width:12px"></i>
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

function showToast(msg, type="success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    // Estilo Apple para toast
    toast.style.background = "var(--layer-2)";
    toast.style.border = "1px solid var(--border-ghost)";
    toast.style.borderRadius = "8px";
    toast.style.padding = "12px 16px";
    toast.style.boxShadow = "var(--shadow-md)";
    toast.style.color = "var(--text-100)";
    toast.style.display = "flex";
    toast.style.alignItems = "center";
    toast.style.gap = "10px";
    toast.style.marginBottom = "10px";
    toast.style.fontSize = "0.85rem";

    const iconColor = type === 'success' ? 'var(--hot)' : 'var(--dead)';

    toast.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            ${type === 'success' ? '<polyline points="20 6 9 17 4 12"></polyline>' : '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>'}
        </svg>
        <span>${msg}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s";
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function fireConfetti() {
    const colors = ['#3D7BFF', '#00D97E', '#F5A623', '#EF4444', '#A78BFA'];
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

function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + "a";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + "m";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "min";
    return "agora";
}
