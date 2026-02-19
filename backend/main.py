import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# IMPORTS RELATIVOS (funcionam quando Root Directory = backend)
from routes import tracker
from routes import forms as public_forms
from routes.admin import forms as admin_forms
from routes import leads
from routes import dashboard
from routes import links
from routes.admin import master
from routes import auth

# Carrega variáveis de ambiente
load_dotenv()

app = FastAPI(
    title="Funila API",
    version="1.0.0"
)

# =============================
# CORS CONFIGURATION
# =============================

origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================
# HEALTH CHECK
# =============================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# =============================
# REGISTER ROUTES
# =============================

app.include_router(tracker.router)
app.include_router(public_forms.router)
app.include_router(admin_forms.router)
app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(links.router)
app.include_router(master.router)
app.include_router(auth.router)

# =============================
# STATIC FILES (FRONTEND)
# =============================

# Mount admin panel (e.g. /admin/dashboard.html)
app.mount("/admin", StaticFiles(directory="../frontend/admin", html=True), name="admin")

# Mount master panel
app.mount("/master", StaticFiles(directory="../frontend/master", html=True), name="master")

# Mount public forms frontend
app.mount("/form", StaticFiles(directory="../frontend/form", html=True), name="form")

# Mount login page at root (must be last to avoid overriding other routes)
app.mount("/", StaticFiles(directory="../frontend/login", html=True), name="login")
