document.addEventListener("DOMContentLoaded", async () => {
    const session = await Auth.checkAuth();
    if (session) {
        loadDashboard();
    }
});

let chartInstance = null;

async function loadDashboard() {
    const period = document.getElementById("period-filter").value;
    const session = await Auth.checkAuth(); // ensure token fresh
    const token = session.access_token;

    try {
        const res = await fetch(`${Auth.API_URL}/metrics?period=${period}`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!res.ok) throw new Error("Failed to fetch metrics");

        const data = await res.json();
        updateUI(data);

    } catch (err) {
        console.error(err);
    }
}

function updateUI(data) {
    document.getElementById("val-clicks").innerText = data.metrics.clicks;
    document.getElementById("val-leads").innerText = data.metrics.leads;
    document.getElementById("val-hot").innerText = data.metrics.hot_leads;
    document.getElementById("val-conv").innerText = data.metrics.conversion_rate + "%";

    // Chart
    const ctx = document.getElementById('leadsChart').getContext('2d');

    if (chartInstance) {
        chartInstance.destroy();
    }

    const labels = data.chart_data.map(d => d.date);
    const values = data.chart_data.map(d => d.count);

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Leads por Dia',
                data: values,
                borderColor: '#2563EB',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#2A3242' } },
                x: { grid: { display: false } }
            }
        }
    });
}
