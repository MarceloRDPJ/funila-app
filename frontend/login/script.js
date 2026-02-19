const SUPABASE_URL  = "https://qitbyswmidyakadrzatz.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpdGJ5c3dtaWR5YWthZHJ6YXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MDQ3NzAsImV4cCI6MjA4NzA4MDc3MH0.FHUD9EuHNOnxv7UALkHNlLiEZv5Q7yYvT9GIz3QeSl0";
// If served from the same backend, we can use relative paths.
// Otherwise, use "https://funila-api.onrender.com";
const API_URL = "";

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

async function checkAlreadyLoggedIn() {
    const sb = getSupabase();
    const { data: { session } } = await sb.auth.getSession();

    if (session) {
        // Already logged in, redirect
        console.log("Already logged in, redirecting...");
        await handleRedirect(session);
    }
}

async function handleRedirect(session) {
    try {
        const token = session.access_token;
        // Fetch user role
        const res = await fetch(`${API_URL}/auth/me`, {
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
            // Error fetching role, maybe logout?
            console.error("Error fetching role");
            // Optionally logout if role fetch fails
            // await getSupabase().auth.signOut();
        }
    } catch (e) {
        console.error("Redirect error:", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    checkAlreadyLoggedIn();

    const form = document.getElementById("login-form");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const btn = form.querySelector("button[type='submit']");
    const errorMsg = document.getElementById("error-message");
    const spinner = btn.querySelector(".spinner");
    const btnText = btn.querySelector("span");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = emailInput.value;
        const password = passwordInput.value;

        // Reset UI
        errorMsg.style.display = "none";
        btn.disabled = true;
        btnText.style.display = "none";
        spinner.style.display = "block";

        try {
            const sb = getSupabase();
            const { data, error } = await sb.auth.signInWithPassword({
                email: email,
                password: password
            });

            if (error) throw error;

            // Login successful
            await handleRedirect(data.session);

        } catch (err) {
            console.error(err);
            errorMsg.innerText = "E-mail ou senha incorretos. Tente novamente.";
            errorMsg.style.display = "block";
            btn.disabled = false;
            btnText.style.display = "block";
            spinner.style.display = "none";
        }
    });
});
