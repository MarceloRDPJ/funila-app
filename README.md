# Funila — Sistema de Inteligência Comercial B2B

O **Funila** é um sistema SaaS B2B de alta performance desenvolvido para agências, corretores e times de vendas. Não é apenas um CRM, mas uma **camada de inteligência** entre o tráfego pago e o fechamento da venda.

Ele combina um SDR digital automatizado, monitoramento de criativos (utm_content), enriquecimento de dados (BrasilAPI, Serasa, WhatsApp) e gestão visual de pipeline (Kanban).

---

## 🚀 Filosofia do Produto

1.  **Inteligência antes da Conversa:** O lead chega ao vendedor já qualificado e enriquecido.
2.  **SDR Automático:** O sistema filtra curiosos e prioriza leads quentes.
3.  **Atribuição Real:** Monitoramento granular de criativos e etapas de funil.
4.  **Anti-Burrice:** Interfaces guiadas que impedem erros operacionais.
5.  **Performance:** Stack leve (FastAPI + Vanilla JS) focada em velocidade e conversão.

---

## 🛠 Stack Tecnológica (Obrigatória)

*   **Backend:** Python 3.11 + FastAPI + Pydantic v2
*   **Database:** Supabase (PostgreSQL 16) com RLS e RPC
*   **Frontend:** HTML5, CSS3, Vanilla JS (Sem frameworks pesados)
*   **Libs:** SortableJS (Kanban), Chart.js (Dashboard)
*   **Infra:** Render (API), GitHub Pages (Frontend), Supabase (Auth/DB)

---

## 🔐 Segurança e Privacidade

*   **Autenticação:** JWT via Supabase Auth.
*   **RLS (Row Level Security):** Isolamento total de dados entre clientes (Multi-tenant).
*   **Criptografia:** Dados sensíveis (CPF) criptografados no banco.
*   **LGPD:** Consentimento explícito e anonimização de IPs.
*   **CORS:** Configurado via Regex para permitir scanner em sites de clientes e bloquear outros acessos.

---

## 📂 Estrutura de Pastas

```
/
├── backend/            # API Python (FastAPI)
│   ├── routes/         # Endpoints (leads, admin, tracker)
│   ├── services/       # Lógica de negócios (enrichment, webhooks)
│   ├── utils/          # Criptografia, helpers
│   └── main.py         # Entry point da aplicação
├── database/           # Migrations e schemas SQL
├── docs/               # Documentação técnica e manuais
├── frontend/           # Interface do usuário (Admin + Forms)
│   ├── admin/          # Painel do Cliente (Kanban, Dashboards)
│   ├── assets/         # Imagens e ícones
│   ├── js/             # Scripts (Auth, Scanner)
│   └── scanner.js      # Script de rastreamento externo
└── ...
```

---

## 📜 Licença

Este software é proprietário e confidencial. Todos os direitos reservados à **Funila Tecnologia**.
O uso, cópia, modificação ou distribuição não autorizada deste código é estritamente proibido.

Copyright © 2026 Funila.

---

## 📞 Suporte e Documentação

Para detalhes sobre permissões e hierarquia, consulte [docs/PERMISSIONS.md](docs/PERMISSIONS.md).
Para deploy e instalação, veja [docs/DEPLOY.md](docs/DEPLOY.md).
