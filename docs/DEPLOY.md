# Guia de Deploy - Funila

Este documento descreve as etapas necessárias para configurar e implantar o backend e frontend do Funila.

## Requisitos de Ambiente (Backend)

O backend é construído em Python (FastAPI). Ao implantar no **Render** (ou qualquer outro provedor), você **DEVE** configurar as seguintes variáveis de ambiente:

### Variáveis Críticas (Obrigatórias)

| Variável | Descrição |
| :--- | :--- |
| `SUPABASE_URL` | URL do projeto Supabase. |
| `SUPABASE_SERVICE_KEY` | Chave de serviço (Service Role) do Supabase. |
| `ENCRYPTION_KEY` | **CRÍTICO:** Chave AES-256 para criptografia de dados sensíveis (CPF). |

> **⚠️ Atenção:** Se `ENCRYPTION_KEY` não for configurada, o servidor **não iniciará** (crash no startup) para evitar processamento inseguro de dados.

### Como Gerar a `ENCRYPTION_KEY`

Execute o seguinte comando Python localmente para gerar uma chave segura:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copie a saída (string base64) e cole no painel de variáveis de ambiente do seu provedor de hospedagem.

### Outras Variáveis

| Variável | Descrição | Padrão |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Define o ambiente (`production` ou `development`). | `production` |
| `CORS_ORIGINS` | Lista de origens permitidas separadas por vírgula. | `*` |
| `SOAWS_TOKEN` | Token para consulta de CPF/CNPJ (SOA Webservices). | (Opcional) |
| `RESEND_API_KEY` | Chave da API Resend para envio de e-mails transacionais. | (Opcional) |

## Frontend

O frontend é estático (HTML/JS/CSS). Certifique-se de que a URL da API esteja configurada corretamente nos arquivos JS (geralmente em `auth.js` ou `app.js`).

- Em produção, o frontend deve apontar para a URL do backend implantado.
- Verifique `frontend/form/app.js`, `frontend/admin/js/auth.js`, etc.

## Checklist de Produção

1. [ ] Variáveis de ambiente configuradas no Render/Vercel.
2. [ ] `ENCRYPTION_KEY` gerada e salva.
3. [ ] Banco de dados Supabase com as tabelas e triggers criados.
4. [ ] URLs de redirecionamento (Redirect URLs) configuradas no Supabase Auth.
