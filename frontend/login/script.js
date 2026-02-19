const SUPABASE_URL = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";
const API_URL = "https://funila-app.onrender.com";

let supabaseClient = null;

function getSupabase() {
    if (!supabaseClient) {
        if (typeof supabase === "undefined") {
            console.error("Supabase JS not loaded");
            return null;
        }
        supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    }
    return supabaseClient;
}

function togglePassword() {
    const passwordInput = document.getElementById("password");
    const eyeOpen = document.getElementById("eye-open");
    const eyeClosed = document.getElementById("eye-closed");
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        eyeOpen.style.display = "none";
        eyeClosed.style.display = "block";
    } else {
        passwordInput.type = "password";
        eyeOpen.style.display = "block";
        eyeClosed.style.display = "none";
    }
}

async function handleRedirect(session) {
    try {
        const token = session.access_token;
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            const profile = await res.json();
            if (profile.role === "master") {
                window.location.href = "/frontend/master/index.html";
            } else {
                window.location.href = "/frontend/admin/dashboard.html";
            }
        } else {
            // Não conseguiu buscar o role — desloga e mostra erro
            await getSupabase().auth.signOut();
            showError("Erro ao verificar permissões. Tente novamente.");
        }
    } catch (e) {
        console.error("Redirect error:", e);
        showError("Erro de conexão. Tente novamente.");
    }
}

async function checkAlreadyLoggedIn() {
    const sb = getSupabase();
    if (!sb) return;
    const { data: { session } } = await sb.auth.getSession();
    if (session) {
        await handleRedirect(session);
    }
}

function showError(msg) {
    const errorMsg = document.getElementById("error-message");
    errorMsg.innerText = msg;
    errorMsg.style.display = "block";
}

function resetBtn() {
    const btn = document.querySelector("button[type='submit']");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector("span");
    btn.disabled = false;
    btnText.style.display = "block";
    spinner.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
    checkAlreadyLoggedIn();

    const form = document.getElementById("login-form");
    const btn = form.querySelector("button[type='submit']");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector("span");
    const errorMsg = document.getElementById("error-message");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        // Reset UI
        errorMsg.style.display = "none";
        btn.disabled = true;
        btnText.style.display = "none";
        spinner.style.display = "block";

        try {
            const sb = getSupabase();
            const { data, error } = await sb.auth.signInWithPassword({ email, password });

            if (error) throw error;

            await handleRedirect(data.session);

        } catch (err) {
            console.error(err);
            showError("E-mail ou senha incorretos. Tente novamente.");
            resetBtn();
        }
    });
});
