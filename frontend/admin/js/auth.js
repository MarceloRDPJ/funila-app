// Supabase Configuration
// REPLACE THESE WITH YOUR ACTUAL SUPABASE KEYS
const SUPABASE_URL = "https://your-project.supabase.co";
const SUPABASE_ANON_KEY = "your-anon-key";
const API_URL = "http://localhost:8000"; // API Backend URL

let supabaseClient = null;

function getSupabase() {
    if (!supabaseClient) {
        if (typeof supabase === 'undefined') {
            console.error("Supabase JS not loaded");
            return null;
        }
        supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
    return supabaseClient;
}

async function checkAuth() {
    const sb = getSupabase();
    const { data: { session } } = await sb.auth.getSession();

    if (!session) {
        // Redirect to login if not already there
        if (!window.location.pathname.includes("login.html")) {
            window.location.href = "index.html";
        }
        return null;
    }

    // If on login page and authenticated, go to dashboard
    if (window.location.pathname.includes("index.html") || window.location.pathname.endsWith("/admin/")) {
        window.location.href = "dashboard.html";
    }

    return session;
}

async function login(email, password) {
    const sb = getSupabase();
    const { data, error } = await sb.auth.signInWithPassword({
        email: email,
        password: password,
    });

    if (error) throw error;

    // Fetch Role to determine redirect
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
        console.error("Failed to fetch role", e);
    }

    return data;
}

async function logout() {
    const sb = getSupabase();
    await sb.auth.signOut();
    window.location.href = "index.html";
}

// Attach to window for easy access
window.Auth = {
    checkAuth,
    login,
    logout,
    getSupabase,
    API_URL
};
