import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def run(playwright):
    # Start HTTP server from root
    server = subprocess.Popen([sys.executable, "-m", "http.server", "8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Server started on 8000")
    time.sleep(3)

    try:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Robust Auth Mock: prevent auth.js from overwriting
        page.add_init_script("""
            window.mockAuth = {
                checkAuth: async () => ({ access_token: "dummy_token", user: { id: "1" } }),
                API_URL: "https://funila-app.onrender.com",
                logout: () => {},
                getToken: async () => "dummy_token"
            };

            // Override window.Auth when it tries to set itself
            Object.defineProperty(window, 'Auth', {
                get: () => window.mockAuth,
                set: (val) => { console.log("Auth set blocked"); }
            });
        """)

        # Mock API Responses
        def handle_api(route):
            url = route.request.url
            print(f"Intercepted: {url}")
            if "metrics/abandonment" in url:
                route.fulfill(json={"step_1_drop_rate": 0.25})
            elif "metrics" in url:
                route.fulfill(json={
                    "metrics": {"clicks": 1250, "leads": 85, "hot_leads": 12, "conversion_rate": 6.8},
                    "breakdown": {"hot": 12, "warm": 40, "cold": 25, "converted": 8},
                    "chart_data": [{"date": "2023-10-01", "count": 10}, {"date": "2023-10-02", "count": 15}, {"date": "2023-10-03", "count": 20}, {"date": "2023-10-04", "count": 12}, {"date": "2023-10-05", "count": 18}, {"date": "2023-10-06", "count": 25}, {"date": "2023-10-07", "count": 22}]
                })
            elif "funnel" in url:
                route.fulfill(json={
                    "counts": {"step_1": 1000, "step_2": 800, "step_3": 500, "converted": 85},
                    "rates": {"step_1_to_2": 80, "step_2_to_3": 62.5, "step_3_to_conv": 17}
                })
            elif "leads" in url:
                route.fulfill(json={
                    "data": [
                        {"id": "1", "name": "João Silva", "status": "hot", "internal_score": 85, "external_score": 0, "phone": "11999999999", "created_at": "2023-10-07T10:00:00Z", "step_reached": 99, "utm_source": "Google"},
                        {"id": "2", "name": "Maria Souza", "status": "warm", "internal_score": 55, "external_score": 0, "phone": "11888888888", "created_at": "2023-10-06T14:30:00Z", "step_reached": 2, "utm_source": "Facebook"},
                        {"id": "3", "name": "Pedro Santos", "status": "abandoned", "internal_score": 20, "external_score": 0, "phone": "11777777777", "created_at": "2023-10-07T09:15:00Z", "step_reached": 1, "utm_source": "Direct"}
                    ],
                    "total": 3, "page": 1, "limit": 100
                })
            else:
                route.continue_()

        # Intercept any request to funila-app.onrender.com
        page.route("**/*funila-app.onrender.com/**", handle_api)

        # 1. Dashboard
        print("Navigating to Dashboard...")
        try:
            page.goto("http://localhost:8000/frontend/admin/dashboard.html", timeout=30000)
            page.wait_for_timeout(3000) # Wait for JS to render
            page.screenshot(path="verification/dashboard_sprint1.png")
            print("Dashboard screenshot taken.")
        except Exception as e:
            print(f"Dashboard failed: {e}")

        # 2. Leads (Kanban)
        print("Navigating to Leads...")
        try:
            page.goto("http://localhost:8000/frontend/admin/leads.html", timeout=30000)
            page.wait_for_timeout(3000) # Wait for JS to render
            page.screenshot(path="verification/leads_sprint1.png")
            print("Leads screenshot taken.")
        except Exception as e:
            print(f"Leads failed: {e}")

        browser.close()
    finally:
        server.terminate()
        print("Server stopped")

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
