import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from routes import tracker
from routes import forms as public_forms
from routes.admin import forms as admin_forms
from routes import leads
from routes import dashboard
from routes import links
from routes.admin import master
from routes import auth
from routes import scanner
from routes import analytics
from routes import oauth
from routes import creatives
from routes import billing
from routes import logs
from services.meta_sync import sync_meta_account
from database import get_supabase

load_dotenv()

app = FastAPI(title="Funila API", version="1.0.0")
scheduler = AsyncIOScheduler()

async def sync_all_accounts():
    try:
        supabase = get_supabase()
        if supabase:
            # Fetch distinct client_ids that have ad_accounts
            res = supabase.table('ad_accounts').select('client_id').execute()
            if res.data:
                client_ids = set(acc['client_id'] for acc in res.data)
                for cid in client_ids:
                    await sync_meta_account(cid)
    except Exception as e:
        print(f"Scheduler Sync Error: {e}")

@app.on_event('startup')
async def startup_event():
    try:
        scheduler.add_job(sync_all_accounts, 'interval', hours=4)
        scheduler.start()
    except Exception as e:
        print(f"Scheduler startup error: {e}")

# CORS Configuration
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://funila-app.onrender.com,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT", "production")}

# ------------------------------------------------------------------------------
# API ROUTERS (Must be included BEFORE StaticFiles to avoid shadowing)
# ------------------------------------------------------------------------------
app.include_router(tracker.router)
app.include_router(public_forms.router)
app.include_router(admin_forms.router)
app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(links.router)
app.include_router(master.router)
app.include_router(auth.router)
app.include_router(scanner.router)
app.include_router(analytics.router)
app.include_router(oauth.router)
app.include_router(creatives.router)
app.include_router(billing.router)
app.include_router(logs.router)

# ------------------------------------------------------------------------------
# STATIC FILES (Frontend)
# ------------------------------------------------------------------------------
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

if os.path.exists(frontend_dir):
    # Mount specific sections to handle relative paths correctly
    # Check if directories exist before mounting to avoid errors
    master_dir = os.path.join(frontend_dir, "master")
    if os.path.exists(master_dir):
        app.mount("/master", StaticFiles(directory=master_dir, html=True), name="master")

    admin_dir = os.path.join(frontend_dir, "admin")
    if os.path.exists(admin_dir):
        app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")

    login_dir = os.path.join(frontend_dir, "login")
    if os.path.exists(login_dir):
        app.mount("/login", StaticFiles(directory=login_dir, html=True), name="login")

    # Mount the entire frontend directory at /frontend for legacy/shared assets access
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {frontend_dir}")

# Serve the root index.html (landing page or main entry)
@app.get("/")
async def read_root():
    index_path = os.path.join(frontend_dir, "../index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # If root index.html doesn't exist, try frontend/index.html or redirect to login
    frontend_index = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_index):
         return FileResponse(frontend_index)
    return RedirectResponse(url="/login")
