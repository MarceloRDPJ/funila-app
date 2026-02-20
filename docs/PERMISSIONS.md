# Hierarquia de Perfis e Permissões (Funila B2B)

O sistema Funila opera com isolamento rigoroso de dados através de **RLS (Row Level Security)** no PostgreSQL, garantindo que usuários vejam apenas o que têm permissão.

## 📌 Níveis de Acesso

### 1. **Master Admin (Superusuário)**

*   **Descrição:** O "Deus" do sistema. Acesso irrestrito a todas as configurações globais e dados de todos os clientes.
*   **Permissões:**
    *   Criar/Editar/Excluir **Clientes** (Agências, Corretores).
    *   Gerenciar **Assinaturas** (Free, Pro, Agency).
    *   Acessar **Métricas Globais** de todos os tenants.
    *   Configurar chaves de API globais (Serasa, WhatsApp).
*   **Acesso:** Painel Master (`/admin/master`).
*   **Segurança:** Autenticação JWT com claim `role: master`.

### 2. **Client Admin (Agência/Corretor)**

*   **Descrição:** O cliente pagante do SaaS. Administra seus próprios leads e equipe.
*   **Permissões:**
    *   **Dashboard:** Ver métricas de conversão e leads (apenas os seus).
    *   **CRM Kanban:** Gerenciar leads (arrastar, editar status, anotações).
    *   **Criativos:** Monitorar performance de seus anúncios (clicks, steps, conversão).
    *   **Formulários:** Configurar campos personalizados e links de rastreamento.
    *   **Webhooks:** Configurar integrações (apenas para seus leads).
*   **Restrições:**
    *   NÃO vê dados de outros clientes.
    *   NÃO altera configurações globais do sistema.
*   **Acesso:** Painel do Cliente (`/admin/dashboard`, `/admin/leads`, `/admin/creatives`).
*   **Segurança:** Autenticação JWT vinculada a `client_id` na tabela `public.users`.
*   **RLS Policy:** `client_id = auth.uid()` (ou similar via tabela de relacionamento).

### 3. **Lead (Visitante/Usuário Final)**

*   **Descrição:** O potencial cliente capturado pelo sistema.
*   **Permissões:**
    *   **Público:** Preencher formulários (`/form`).
    *   **Rastreamento:** Ser monitorado pelo `scanner.js` (Beacon).
*   **Restrições:**
    *   Nenhum acesso administrativo.
*   **Segurança:** Sessão anônima (`visitor_session`) ou cookie de rastreamento. Não requer login.

---

## 🔒 Políticas de Segurança (RLS)

A segurança é garantida no nível do banco de dados, independente da aplicação.

### Tabela: `leads`

```sql
CREATE POLICY "client_leads" ON leads FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));
```
*   **Efeito:** O usuário logado só vê leads onde o `client_id` bate com o seu registro na tabela `users`.

### Tabela: `creative_metrics`

```sql
CREATE POLICY "client_creative_metrics" ON creative_metrics FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));
```
*   **Efeito:** O cliente só vê métricas dos seus próprios criativos.

### Tabela: `webhooks`

```sql
CREATE POLICY "client_webhooks" ON webhooks FOR ALL
    USING (client_id = (SELECT client_id FROM public.users WHERE id = auth.uid()));
```
*   **Efeito:** O cliente só gerencia seus próprios webhooks.

---

## 🛡️ Autenticação e Sessão

1.  **Login:** O usuário faz login via Supabase Auth (Email/Senha).
2.  **Token:** Recebe um JWT contendo o `sub` (User ID).
3.  **Role Check:** O backend verifica na tabela `public.users` qual o `role` e `client_id` associado.
4.  **Sessão:** O frontend armazena o token e o utiliza no header `Authorization: Bearer <token>` para todas as requisições à API.

---

## ⚠️ Pontos Críticos

*   **Anti-Race Condition:** Métricas de cliques (`creative_metrics`) usam funções RPC atômicas (`increment_creative_metric`) para evitar contagem incorreta em acessos simultâneos.
*   **Isolamento:** Nunca remova o filtro `client_id` das queries, mesmo que o RLS esteja ativo (segurança em profundidade).
*   **Scanner Público:** O endpoint `/scanner/event` é público (sem auth), mas apenas insere dados (Write-Only). Não permite leitura.
