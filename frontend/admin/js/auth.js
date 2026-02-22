const SUPABASE_URL     = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";

// ✅ Detecção de ambiente robusta (Fix Bug #4)
function resolveApiUrl() {
  const h = window.location.hostname;
  if (h === 'localhost' || h === '127.0.0.1') return 'http://localhost:8000';
  if (h === 'app.funila.com.br')             return 'https://funila-app.onrender.com';
  if (h.includes('github.io'))               return 'https://funila-app.onrender.com';
  // Fallback: mesmo host (Render servindo frontend junto)
  return window.location.origin;
}
const API_URL = resolveApiUrl();

let supabaseClient = null;

function getSupabase() {
    if (!supabaseClient) {
        if (typeof supabase === "undefined") {
            console.error("Supabase JS não carregado");
            return null;
        }
        supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
    return supabaseClient;
}

async function checkAuth() {
    const sb = getSupabase();
    if (!sb) return null;
    const { data: { session } } = await sb.auth.getSession();
    if (!session) {
        if (!window.location.pathname.includes("/login/")) {
            logout(); // Usa a função logout corrigida
        }
        return null;
    }

    // Atualiza interface com dados do usuário
    updateUserProfile(session);

    return session;
}

// ✅ Fix UX: Master não tem client_id, então tratamos o erro visual
async function updateUserProfile(session) {
    try {
        const token = getToken(session);
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        // Se for master sem impersonation, o backend pode retornar erro ou dados parciais.
        // Vamos tentar parsear mesmo com erro para ver se vem role='master'
        let user = {};
        if (res.ok) {
            user = await res.json();
        } else {
             // Fallback simples se falhar
             console.warn("Auth/me failed, assuming default state");
        }

        // Se o token indica master (podemos decodificar JWT, mas aqui confiamos no backend ou defaults)
        // O backend geralmente retorna role='master' no /auth/me se tiver autenticado.

        // Update DOM elements
        document.querySelectorAll(".client-name").forEach(el => el.textContent = user.name || "Usuário");
        document.querySelectorAll(".client-plan, .plan-name").forEach(el => el.textContent = user.plan || "Solo");
        document.querySelectorAll(".client-avatar, .user-avatar").forEach(el => el.textContent = user.avatar_initials || "US");

        // ✅ Esconder créditos/upgrade para master (Fix UX)
        if (user.role === 'master') {
            document.querySelectorAll('.credits-footer, .btn-upgrade, .upgrade-btn').forEach(
                el => el.style.display = 'none');
            // Forçar nome se vier vazio
            document.querySelectorAll(".client-name").forEach(el => {
                if(el.textContent === "Usuário") el.textContent = "Administrador";
            });
        }

    } catch (e) {
        console.error("Error updating user profile", e);
    }
}

// ✅ Logout com redirect correto (Fix Bug #4)
async function logout() {
    const sb = getSupabase();
    await sb.auth.signOut();
    sessionStorage.clear();

    // Path correto dependendo de onde o frontend está
    // Se estiver no GitHub Pages (path prefix /funila-app/), ajusta.
    // Se estiver em produção (root), usa /login/

    const isGithub = window.location.hostname.includes('github.io');
    const loginUrl = isGithub ? '/funila-app/frontend/login/index.html' : '/login/';

    window.location.href = loginUrl;
}

function getToken(session) {
    const custom = sessionStorage.getItem('custom_access_token');
    if (custom) return custom;
    if (session && session.access_token) return session.access_token;
    return null;
}

async function getTokenAsync() {
    const custom = sessionStorage.getItem('custom_access_token');
    if (custom) return custom;
    const sb = getSupabase();
    const { data: { session } } = await sb.auth.getSession();
    return session?.access_token || null;
}

async function authHeaders(session) {
    const token = session ? getToken(session) : await getTokenAsync();
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

// Global Toast System
function showToast(message, type = "success", action = null) {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let icon = "";
    if (type === "success") {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "error") {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
        icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    let actionBtn = "";
    if (action) {
        // Safe closure handling
        const btnId = `toast-action-${Date.now()}`;
        setTimeout(() => {
            const btn = document.getElementById(btnId);
            if(btn) btn.onclick = action.callback;
        }, 0);
        actionBtn = `<button id="${btnId}" style="margin-left:auto;background:none;border:none;color:inherit;text-decoration:underline;font-size:0.75rem;cursor:pointer;font-weight:600">${action.label}</button>`;
    }

    toast.innerHTML = `${icon} <span style="flex:1">${message}</span> ${actionBtn}`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        setTimeout(() => toast.remove(), 300);
    }, 5000); // 5 seconds for actionable toasts
}

// ══════════════════════════════════════════
// SHARED UI LOGIC (Sidebar, Header Buttons)
// ══════════════════════════════════════════

function openSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.add("open");
    if (overlay) overlay.classList.add("open");
}

function closeSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");
    if (sidebar) sidebar.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
}

function setupUI() {
    // Theme Toggle
    const btnTheme = document.getElementById("btn-theme");
    if (btnTheme) {
        btnTheme.onclick = () => showToast("Tema claro disponível em breve", "info");
    }

    // Notifications
    const btnNotifs = document.getElementById("btn-notifs");
    if (btnNotifs) {
        btnNotifs.onclick = () => showToast("Você não tem novas notificações", "info");
    }

    // Profile
    const btnProfile = document.getElementById("btn-profile");
    if (btnProfile) {
        btnProfile.onclick = () => window.location.href = "settings.html";
    }
}

// ✅ Standard Empty State Renderer (Fix UX)
function renderEmptyState(containerId, icon, title, subtitle) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                    padding:64px 24px;color:var(--text-40);text-align:center;min-height:200px">
            <div style="font-size:2.5rem;margin-bottom:16px;opacity:0.6">${icon}</div>
            <div style="font-size:0.9rem;color:var(--text-70);font-weight:500;margin-bottom:6px">${title}</div>
            <div style="font-size:0.78rem;line-height:1.5">${subtitle}</div>
        </div>`;
}

function exitImpersonation() {
    sessionStorage.removeItem('custom_access_token');
    const masterToken = sessionStorage.getItem('master_token_backup');
    if (masterToken) {
        window.location.href = '/frontend/master/index.html';
    } else {
        window.location.href = '/frontend/login/index.html';
    }
}

// Initialize UI when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    setupUI();

    // Detecta impersonação ativa e exibe banner
    const customToken = sessionStorage.getItem('custom_access_token');
    if (customToken) {
        const existing = document.getElementById('impersonation-banner');
        if (existing) {
            existing.style.display = 'flex';
        } else {
            const banner = document.createElement('div');
            banner.id = 'impersonation-banner-fixed';
            banner.style.cssText = `
                position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
                background:var(--warm-bg);border:1px solid var(--warm);color:var(--warm);
                padding:8px 16px;border-radius:20px;font-size:0.75rem;font-weight:600;
                display:flex;align-items:center;gap:12px;z-index:9999;
                box-shadow:0 4px 20px rgba(0,0,0,0.4);white-space:nowrap`;
            banner.innerHTML = `
                ⚠ Você está no painel de um cliente
                <button onclick="exitImpersonation()" style="background:var(--warm);color:#000;border:none;
                    border-radius:10px;padding:3px 10px;font-size:0.72rem;font-weight:700;cursor:pointer">
                    Sair
                </button>`;
            document.body.appendChild(banner);
        }
    }
});

window.Auth = { checkAuth, logout, getSupabase, getToken, getTokenAsync, authHeaders, API_URL, showToast };
window.showToast = showToast;
window.renderEmptyState = renderEmptyState;
window.exitImpersonation = exitImpersonation;
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;
