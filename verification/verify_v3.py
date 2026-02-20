from playwright.sync_api import sync_playwright
import os

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Mock API responses
    page.route("**/forms/config/*", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"client_name":"Cliente Teste","finish_action":"message","fields":[{"field_key":"full_name","label":"Nome","order":0,"type":"text","required":true}]}'
    ))
    page.route("**/admin/forms/", lambda route: route.fulfill(
        status=200, content_type="application/json", body='[{"field_id":"1","field_key":"test","label_default":"Teste","label_custom":"Custom","active":true,"required":false}]'
    ))
    # Mock Leads API for CRM
    page.route("**/leads?*", lambda route: route.fulfill(
        status=200, content_type="application/json", body='{"data":[{"id":"1","name":"João Silva","phone":"11999999999","status":"started","internal_score":10,"external_score":0,"created_at":"2023-10-27T10:00:00","consent_given":false},{"id":"2","name":"Maria Souza","phone":"11888888888","status":"hot","internal_score":80,"external_score":0,"created_at":"2023-10-26T15:30:00","consent_given":true}],"total":2,"page":1,"limit":10}'
    ))

    page.route("**/js/auth.js", lambda route: route.fulfill(
        status=200, content_type="application/javascript", body='window.Auth = { checkAuth: async () => ({ access_token: "fake" }), logout: async () => {}, API_URL: "https://funila-app.onrender.com" };'
    ))

    cwd = os.getcwd()

    # Verify Landing Page V3
    landing_path = f"file://{cwd}/frontend/landing/index.html"
    print(f"Navigating to {landing_path}")
    page.goto(landing_path)
    page.wait_for_timeout(2000)
    page.screenshot(path="verification/landing_v3.png", full_page=True)

    # Verify CRM Dashboard
    crm_path = f"file://{cwd}/frontend/admin/leads.html"
    print(f"Navigating to {crm_path}")
    page.goto(crm_path)
    page.wait_for_timeout(2000)
    page.screenshot(path="verification/crm_dashboard.png", full_page=True)

    # Verify Admin Config with Capture Toggle
    admin_path = f"file://{cwd}/frontend/admin/forms.html"
    print(f"Navigating to {admin_path}")
    page.goto(admin_path)
    page.wait_for_timeout(2000)
    page.screenshot(path="verification/admin_config_v3.png", full_page=True)

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
