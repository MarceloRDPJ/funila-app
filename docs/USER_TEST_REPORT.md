## Relatório de Teste de Usabilidade (Simulado)

### 1. Perfil Cliente (Marcelo Prego)
**Usuário:** `marceloprego1223@gmail.com`
**Role:** `client` (Agência)

#### A. Fluxo de Login
1.  **Acesso:** Usuário entra em `/admin/login.html`.
2.  **Credenciais:** Insere email e senha.
3.  **Resultado:** JWT retornado com sucesso. Redirecionamento para `/admin/dashboard.html`.
4.  **Verificação:** Frontend armazena token no `localStorage`.

#### B. Painel Dashboard
1.  **Visualização:** Carrega gráficos de leads e conversão.
2.  **Dados:** Vê *apenas* leads associados ao seu `client_id` (RLS ativo).
3.  **Interação:** Tenta acessar `/admin/master` -> **Erro 403 (Forbidden)**. (Correto).

#### C. CRM Kanban (`/admin/leads.html`)
1.  **Layout:** Vê colunas (Frio, Morno, Negociação, Convertido, Descarte).
2.  **Drag & Drop:** Move card de "Frio" para "Morno".
3.  **API:** `PATCH /leads/{id}` enviado com sucesso. Toast "Lead movido".
4.  **Criativo:** O card mostra `utm_content: video_01` (se capturado).
5.  **WhatsApp:** Clica no botão WhatsApp -> Abre `wa.me` com mensagem personalizada.

#### D. Criativos (`/admin/creatives.html`)
1.  **Tabela:** Lista criativos com métricas (Clicks, Steps 1-3, Vendas).
2.  **Retenção:** Barras de progresso visualizam onde o funil "sangra".

---

### 2. Perfil Master Admin
**Usuário:** `admin@funila.com` (Simulado)
**Role:** `master`

#### A. Gestão Global
1.  **Acesso:** Entra em `/admin/master`.
2.  **Clientes:** Cria novo cliente "Imobiliária X".
3.  **Métricas:** Vê total de leads de *todos* os clientes.

---

### 3. Visitante (Lead)
**Acesso:** Link do anúncio `?utm_content=video_promo`

1.  **Scanner:** JS carrega em background.
2.  **Evento:** `page_view` enviado para `/scanner/event` (Beacon).
3.  **Formulário:** Preenche Nome/Zap.
4.  **Enriquecimento:** Backend consulta BrasilAPI (CPF).
5.  **Conversão:** Redirecionado para WhatsApp.
6.  **Métrica:** `creative_metrics` incrementado (step=99, converted=true).
