const SUPABASE_URL  = "https://qitbyswmidyakadrzatz.supabase.co";  // ← substitua
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";            // ← substitua
// Use relative path since we are serving frontend from backend
const API_URL = "";

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
        // Redirect to main login page if not authenticated
        const path = window.location.pathname;
        // Allow staying on public login pages: root, /index.html (root), /admin/index.html, /admin/
        const isPublic = path === "/" || path === "/index.html" || path.includes("/admin/index.html") || path.endsWith("/admin/");

        if (!isPublic) {
            window.location.href = "/";
        }
        return null;
    }

    // If logged in...
    // 1. If on login page (root or admin login), redirect to dashboard
    if (window.location.pathname === "/" ||
        window.location.pathname === "/index.html" ||
        window.location.pathname.includes("/admin/index.html") ||
        (window.location.pathname.endsWith("/admin/") && !window.location.pathname.includes("dashboard"))) {

        // Check role via API to decide where to go (Master or Admin)
        // Since we are already logged in, we can fetch /auth/me
        try {
            const token = session.access_token;
            // Use relative path for API
            const res = await fetch(`${API_URL || ""}/auth/me`, {
                 headers: { "Authorization": `Bearer ${token}` }
            });
            if (res.ok) {
                const profile = await res.json();
                if (profile.role === 'master') {
                    window.location.href = "/master/index.html";
                } else {
                    window.location.href = "/admin/dashboard.html";
                }
            } else {
                 // Fallback
                 window.location.href = "/admin/dashboard.html";
            }
        } catch (e) {
            console.error("Redirect error", e);
            window.location.href = "/admin/dashboard.html";
        }
    }
    return session;
}

async function login(email, password) {
    const sb = getSupabase();
    const { data, error } = await sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
    const token = data.session.access_token;
    try {
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            const profile = await res.json();
            return { ...data, role: profile.role };
        }
    } catch (e) {
        console.error("Erro ao buscar role:", e);
    }
    return data;
}

async function logout() {
    const sb = getSupabase();
    await sb.auth.signOut();
    window.location.href = "/";
}

async function getToken() {
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

window.Auth = { checkAuth, login, logout, getSupabase, getToken, authHeaders, API_URL };
