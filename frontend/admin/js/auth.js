const SUPABASE_URL     = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";

// Determina a URL da API backend dinamicamente
let API_URL = window.location.origin;

// Se estiver rodando no GitHub Pages ou outro domínio frontend,
// a API deve apontar para o backend no Render.
if (window.location.hostname === "app.funila.com.br" || window.location.hostname.includes("github.io")) {
    API_URL = "https://funila-app.onrender.com";
}

// Se estiver rodando localmente (frontend separado), ajuste conforme necessário
if (window.location.hostname === "localhost" && window.location.port === "5500") {
    // Assumindo que o backend roda na porta 8000
    API_URL = "http://localhost:8000";
}

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
            // Ajuste o caminho de redirecionamento se necessário
            const loginPath = "/frontend/login/index.html";
            // Se já estivermos tentando ir para login, não redireciona em loop
            if (!window.location.pathname.endsWith("login/index.html")) {
                 window.location.href = loginPath;
            }
        }
        return null;
    }
    return session;
}

async function logout() {
    const sb = getSupabase();
    await sb.auth.signOut();
    window.location.href = "/frontend/login/index.html";
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

window.Auth = { checkAuth, logout, getSupabase, getToken, getTokenAsync, authHeaders, API_URL };
