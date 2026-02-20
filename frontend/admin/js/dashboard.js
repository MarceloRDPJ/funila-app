let chartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
    const session = await Auth.checkAuth();
    if (session) loadDashboard();
});

async function loadDashboard() {
    const session = await Auth.checkAuth();
    if (!session) return;

    const period = document.getElementById("period-filter").value;
    const token = session.access_token;
    const headers = { "Authorization": `Bearer ${token}` };

    // 1. Carrega Métricas Gerais (Cliques, Leads, Conversão)
    fetch(`${Auth.API_URL}/metrics?period=${period}`, { headers })
    .then(r => {
        if (!r.ok) throw new Error("Erro metrics");
        return r.json();
    })
    .then(data => {
        renderMetrics(data);
        renderChart(data.chart_data);
        renderBreakdown(data.breakdown);
    })
    .catch(console.error);

    // 2. Carrega Funil Detalhado
    fetch(`${Auth.API_URL}/funnel?period=${period}`, { headers })
    .then(r => {
        if (!r.ok) throw new Error("Erro funnel");
        return r.json();
    })
    .then(renderFunnel)
    .catch(console.error);

    // 3. Carrega Abandono (Novo Card)
    fetch(`${Auth.API_URL}/metrics/abandonment`, { headers })
    .then(r => {
        if (!r.ok) throw new Error("Erro abandonment");
        return r.json();
    })
    .then(data => {
        // Usa a taxa de abandono da etapa 1 como indicador principal,
        // ou uma média. Vamos usar step_1_drop_rate (Visitantes que não passaram para etapa 2)
        // Se desejar abandono total do funil: (1 - conversão)
        // O requisito pede "Abandono no Funil". Vamos mostrar a taxa de queda da primeira etapa que é crítica.
        // Ou o step_1_drop_rate * 100.
        const abandonment = (data.step_1_drop_rate || 0) * 100;
        document.getElementById("val-abandon").textContent = Math.round(abandonment) + "%";
    })
    .catch(err => {
        console.error(err);
        document.getElementById("val-abandon").textContent = "—%";
    });
}

function renderMetrics(data) {
    const m = data.metrics;
    document.getElementById("val-clicks").textContent = m.clicks.toLocaleString("pt-BR");
    document.getElementById("val-leads").textContent  = m.leads.toLocaleString("pt-BR");
    if(document.getElementById("val-hot"))
        document.getElementById("val-hot").textContent = (m.hot_leads || 0).toLocaleString("pt-BR");
    document.getElementById("val-conv").textContent   = m.conversion_rate + "%";
}

function renderFunnel(data) {
    document.getElementById("f-step1").textContent = data.counts.step_1.toLocaleString("pt-BR");
    document.getElementById("f-step2").textContent = data.counts.step_2.toLocaleString("pt-BR");
    document.getElementById("f-step3").textContent = data.counts.step_3.toLocaleString("pt-BR");
    document.getElementById("f-conv").textContent  = data.counts.converted.toLocaleString("pt-BR");

    document.getElementById("f-rate1").textContent = "Total de acessos";
    document.getElementById("f-rate2").textContent = data.rates.step_1_to_2 + "% de avanço";
    document.getElementById("f-rate3").textContent = data.rates.step_2_to_3 + "% de avanço";
    document.getElementById("f-rate4").textContent = data.rates.step_3_to_conv + "% conversão";
}

function renderChart(chartData) {
    const ctx = document.getElementById("leadsChart").getContext("2d");
    const labels = chartData.map(d => {
        const [y, m, day] = d.date.split("-");
        return `${day}/${m}`;
    });
    const values = chartData.map(d => d.count);

    document.getElementById("chart-subtitle").textContent =
        `${values.reduce((a, b) => a + b, 0)} leads`;

    if (chartInstance) chartInstance.destroy();

    // Cores do Sistema de Design para Gráficos
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(37,99,235,0.2)');
    gradient.addColorStop(1, 'rgba(37,99,235,0)');

    chartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Leads",
                data: values,
                borderColor: "#2563EB",
                backgroundColor: gradient,
                borderWidth: 2,
                pointBackgroundColor: "#0F1115",
                pointBorderColor: "#2563EB",
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "#1C212B",
                    borderColor: "#2A3242",
                    borderWidth: 1,
                    titleColor: "#9CA3AF",
                    bodyColor: "#F3F4F6",
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y} leads`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "#2A3242", drawBorder: false },
                    ticks: { color: "#6B7280", font: { size: 11 }, maxTicksLimit: 5, precision: 0 }
                },
                x: {
                    grid: { display: false, drawBorder: false },
                    ticks: { color: "#6B7280", font: { size: 11 } }
                }
            }
        }
    });
}

function renderBreakdown(breakdown) {
    const map = [
        { key: "hot",       label: "Quentes",   color: "var(--hot)" },
        { key: "warm",      label: "Mornos",    color: "var(--warm)" },
        { key: "cold",      label: "Frios",     color: "var(--cold)" },
        { key: "converted", label: "Convertidos", color: "var(--converted)" }
    ];
    const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;

    const list = document.getElementById("breakdown-list");
    list.innerHTML = map.map(item => {
        const val = breakdown[item.key] || 0;
        const pct = Math.round((val / total) * 100);
        return `
            <div>
                <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                    <span style="font-size:.85rem;color:var(--text-secondary)">${item.label}</span>
                    <span style="font-size:.85rem;font-weight:600;color:${item.color}">${val}</span>
                </div>
                <div style="background:rgba(255,255,255,.06);border-radius:99px;height:6px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:${item.color};border-radius:99px;transition:width .6s ease-out"></div>
                </div>
            </div>`;
    }).join("");

    const summary = document.getElementById("summary-list");
    const m = { clicks: 0, leads: total, conversion_rate: 0 };
    summary.innerHTML = `
        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border)">
            <span style="font-size:.9rem;color:var(--text-secondary)">Total de leads</span>
            <span style="font-size:.9rem;font-weight:600;color:var(--text-primary)">${total}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid var(--border)">
            <span style="font-size:.9rem;color:var(--text-secondary)">Convertidos</span>
            <span style="font-size:.9rem;font-weight:600;color:var(--converted)">${breakdown.converted || 0}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:12px 0">
            <span style="font-size:.9rem;color:var(--text-secondary)">Taxa de fechamento</span>
            <span style="font-size:.9rem;font-weight:600;color:var(--text-primary)">${total ? Math.round(((breakdown.converted || 0) / total) * 100) : 0}%</span>
        </div>`;
}

function openSidebar() {
    document.getElementById("sidebar").classList.add("open");
    document.getElementById("sidebar-overlay").classList.add("open");
}
function closeSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebar-overlay").classList.remove("open");
}
