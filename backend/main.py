import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from services.meta_sync import sync_meta_account
from database import get_supabase

load_dotenv()

app = FastAPI(title="Funila API", version="1.0.0")
scheduler = AsyncIOScheduler()

async def sync_all_accounts():
    try:
        supabase = get_supabase()
        # Fetch distinct client_ids that have ad_accounts
        # Supabase doesn't support distinct() in simple client?
        # Just fetch all and set() in python
        res = supabase.table('ad_accounts').select('client_id').execute()
        if res.data:
            client_ids = set(acc['client_id'] for acc in res.data)
            for cid in client_ids:
                await sync_meta_account(cid)
    except Exception as e:
        print(f"Scheduler Sync Error: {e}")

@app.on_event('startup')
async def startup_event():
    scheduler.add_job(sync_all_accounts, 'interval', hours=4)
    scheduler.start()

# CORS Configuration
# Restrict to authorized domains to prevent CSRF/XSS attacks on authenticated endpoints
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
