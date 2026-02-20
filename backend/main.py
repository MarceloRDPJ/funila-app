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

# Permitir CORS para o scanner (que roda em qualquer site do cliente)
# Em produção, idealmente seria restrito aos domínios dos clientes, mas para MVP/SaaS aberto: "*"
origins = os.getenv("CORS_ORIGINS", "https://app.funila.com.br").split(",")
# Adicionar "*" para scanner beacon se necessário, ou configurar dinamicamente.
# Para evitar problemas com credentials, se usarmos "*", allow_credentials deve ser False.
# Mas o dashboard precisa de credentials.
# Solução: Middleware customizado ou confiar na lista de origens.
# Para o scanner (public), usaremos um router separado ou assumiremos que o cliente configura os domínios.
# Vou adicionar "*" na lista de origens para facilitar o beacon, mas com cuidado.
if "*" not in origins:
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
