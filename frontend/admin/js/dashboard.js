let chartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
    const session = await Auth.checkAuth();
    if (session) loadDashboard();
});

async function loadDashboard() {
    const session = await Auth.checkAuth();
    if (!session) return;

    const period = document.getElementById("period-filter").value;

    try {
        const res = await fetch(`${Auth.API_URL}/metrics?period=${period}`, {
            headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        if (!res.ok) throw new Error("Erro ao buscar métricas");
        const data = await res.json();
        renderMetrics(data);
        renderChart(data.chart_data);
        renderBreakdown(data.breakdown);
    } catch (err) {
        console.error(err);
    }
}

function renderMetrics(data) {
    const m = data.metrics;
    document.getElementById("val-clicks").textContent = m.clicks.toLocaleString("pt-BR");
    document.getElementById("val-leads").textContent  = m.leads.toLocaleString("pt-BR");
    document.getElementById("val-hot").textContent    = m.hot_leads.toLocaleString("pt-BR");
    document.getElementById("val-conv").textContent   = m.conversion_rate + "%";
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

    chartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "Leads",
                data: values,
                borderColor: "#3B6EF8",
                backgroundColor: "rgba(59,110,248,0.08)",
                borderWidth: 2,
                pointBackgroundColor: "#3B6EF8",
                pointRadius: 3,
                pointHoverRadius: 5,
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
                    backgroundColor: "#181C24",
                    borderColor: "rgba(255,255,255,0.1)",
                    borderWidth: 1,
                    titleColor: "#8A919E",
                    bodyColor: "#F0F2F5",
                    padding: 10,
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y} lead${ctx.parsed.y !== 1 ? "s" : ""}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
                    ticks: { color: "#8A919E", font: { size: 11 }, maxTicksLimit: 5, precision: 0 }
                },
                x: {
                    grid: { display: false, drawBorder: false },
                    ticks: { color: "#8A919E", font: { size: 11 } }
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
                <div style="display:flex;justify-content:space-between;margin-bottom:5px">
                    <span style="font-size:.8rem;color:var(--text-secondary)">${item.label}</span>
                    <span style="font-size:.8rem;font-weight:600;color:${item.color}">${val}</span>
                </div>
                <div style="background:rgba(255,255,255,.06);border-radius:99px;height:4px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:${item.color};border-radius:99px;transition:width .4s"></div>
                </div>
            </div>`;
    }).join("");

    const summary = document.getElementById("summary-list");
    const m = { clicks: 0, leads: total, conversion_rate: 0 };
    summary.innerHTML = `
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
            <span style="font-size:.85rem;color:var(--text-secondary)">Total de leads</span>
            <span style="font-size:.85rem;font-weight:600">${total}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
            <span style="font-size:.85rem;color:var(--text-secondary)">Convertidos</span>
            <span style="font-size:.85rem;font-weight:600;color:var(--converted)">${breakdown.converted || 0}</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0">
            <span style="font-size:.85rem;color:var(--text-secondary)">Taxa de fechamento</span>
            <span style="font-size:.85rem;font-weight:600">${total ? Math.round(((breakdown.converted || 0) / total) * 100) : 0}%</span>
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
