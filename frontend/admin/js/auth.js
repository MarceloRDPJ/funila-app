const SUPABASE_URL = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";
const API_URL = "https://funila-app.onrender.com";

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

async function getToken() {
    const custom = sessionStorage.getItem('custom_access_token');
    if(custom) return custom;

    const sb = getSupabase();
    const { data: { session } } = await sb.auth.getSession();
    return session?.access_token || null;
}

async function authHeaders() {
    const token = await getToken();
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

window.Auth = { checkAuth, logout, getSupabase, getToken, authHeaders, API_URL };
