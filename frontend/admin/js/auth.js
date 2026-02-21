const SUPABASE_URL     = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";
const API_URL = window.location.origin;

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
            window.location.href = "/frontend/login/index.html";
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

// getToken(session?) — se receber session, retorna token direto (síncrono).
// Se não receber, busca da sessão atual (assíncrono).
// Suporta token de impersonação via sessionStorage.
function getToken(session) {
    // Impersonation override
    const custom = sessionStorage.getItem('custom_access_token');
    if (custom) return custom;

    // Se recebeu session como parâmetro, usa direto — síncrono, sem await
    if (session && session.access_token) return session.access_token;

    // Fallback síncrono — retorna null se não tem cache
    // (use checkAuth() antes para garantir que a sessão existe)
    return null;
}

// getTokenAsync() — garante o token mesmo sem session no parâmetro
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
