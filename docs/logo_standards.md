# Padrões de Logo Funila

Este documento define o uso correto dos ativos de marca na aplicação.

## Arquivos

Os arquivos de logo estão localizados em `frontend/assets/`.

*   **`logo-full.png`**: Logo completo (Ícone + Texto "FUNILA"). Usado em áreas com espaço horizontal suficiente.
    *   **Dimensões recomendadas:** Altura fixa (ex: 32px ou 40px), largura proporcional.
*   **`logo-icon.png`**: Apenas o ícone (símbolo). Usado quando o espaço é restrito ou em mobile.
    *   **Dimensões recomendadas:** Quadrado (ex: 32x32px).
*   **`favicon.png`**: Versão pequena do ícone para abas do navegador.
    *   **Localização:** `frontend/assets/favicon.png`

## Implementação

### 1. Favicon
Todas as páginas HTML devem incluir a seguinte tag no `<head>`:

```html
<link rel="icon" type="image/png" href="/assets/favicon.png">
```

### 2. Landing Page & Login
Utilizam o logo completo (`logo-full.png`) para maximizar o reconhecimento da marca.

```html
<!-- Exemplo na Landing Page -->
<img src="assets/logo-full.png" alt="Funila" class="h-8">
```

### 3. Dashboards (Master e Client)
O sidebar utiliza o logo completo no topo.

```html
<!-- Exemplo no Sidebar -->
<div class="sidebar-header">
    <img src="/assets/logo-full.png" alt="Funila" style="height: 32px;">
</div>
```

## Manutenção

Ao atualizar a marca:
1.  Substitua os arquivos em `frontend/assets/` mantendo os nomes de arquivo originais.
2.  Verifique se as novas dimensões se ajustam aos containers existentes (especialmente no sidebar).
3.  Limpe o cache do navegador para visualizar as alterações.
