import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

load_dotenv()

app = FastAPI(title="Funila API", version="1.0.0")

# CORS Configuration
# Allow any origin to support the public scanner (Beacon/Fetch) on client sites
# Use regex to allow credentials (cookies/auth headers) for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*", # Allow any http/https origin
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
