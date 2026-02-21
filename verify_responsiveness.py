import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

def verify_responsiveness():
    # Start HTTP server
    server_process = subprocess.Popen([sys.executable, "-m", "http.server", "9000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Started HTTP server on port 9000")
    time.sleep(2) # Allow startup

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            print("Starting visual verification...")

            # Mobile Viewport
            context_mobile = browser.new_context(viewport={"width": 375, "height": 812})
            # Inject auth bypass flag
            context_mobile.add_init_script("localStorage.setItem('VISUAL_TEST_MODE', 'true');")

            page_mobile = context_mobile.new_page()
            try:
                page_mobile.goto("http://localhost:9000/frontend/admin/index.html")
                time.sleep(2)
                page_mobile.screenshot(path="verification_admin_mobile.png")
                print("Saved verification_admin_mobile.png")
            except Exception as e:
                print(f"Error mobile: {e}")

            # Tablet Viewport
            context_tablet = browser.new_context(viewport={"width": 768, "height": 1024})
            context_tablet.add_init_script("localStorage.setItem('VISUAL_TEST_MODE', 'true');")

            page_tablet = context_tablet.new_page()
            try:
                page_tablet.goto("http://localhost:9000/frontend/admin/index.html")
                time.sleep(2)
                page_tablet.screenshot(path="verification_admin_tablet.png")
                print("Saved verification_admin_tablet.png")
            except Exception as e:
                print(f"Error tablet: {e}")

            # Desktop Viewport
            context_desktop = browser.new_context(viewport={"width": 1920, "height": 1080})
            context_desktop.add_init_script("localStorage.setItem('VISUAL_TEST_MODE', 'true');")

            page_desktop = context_desktop.new_page()
            try:
                page_desktop.goto("http://localhost:9000/frontend/admin/index.html")
                time.sleep(2)
                page_desktop.screenshot(path="verification_admin_desktop.png")
                print("Saved verification_admin_desktop.png")

                # Check Master Dashboard
                page_desktop.goto("http://localhost:9000/frontend/master/index.html")
                time.sleep(2)
                page_desktop.screenshot(path="verification_master_desktop.png")
                print("Saved verification_master_desktop.png")
            except Exception as e:
                print(f"Error desktop: {e}")

            browser.close()
    finally:
        server_process.kill()
        print("Stopped HTTP server")

if __name__ == "__main__":
    verify_responsiveness()
