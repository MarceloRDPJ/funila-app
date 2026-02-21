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

    if (!leads || leads.length === 0) {
        if (window.renderEmptyState) {
             window.renderEmptyState('kanban-board', '📭', 'Nenhum lead ainda', 'Crie um link de rastreamento e compartilhe nos seus anúncios');
             return;
        }
    }

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
        // Check if element exists before init Sortable
        if (!el) return;

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
                    if (window.showToast) window.showToast(`Movido para ${COLUMN_LABELS[newStatus]}`, "success");

                    if (newStatus === 'converted') {
                        fireConfetti();
                    }
                } catch (error) {
                    if (window.showToast) window.showToast("Erro ao mover lead", "error");
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

    // Atualiza contador total
    const totalEl = document.getElementById('kanban-total');
    if (totalEl) totalEl.textContent = `${leads.length} lead${leads.length !== 1 ? 's' : ''}`;
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
