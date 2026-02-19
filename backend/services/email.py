import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY")

def send_lead_alert(to_email: str, lead_name: str, lead_phone: str, score: int):
    if not resend.api_key or "example" in resend.api_key:
        print(f"Mock Email to {to_email}: Lead {lead_name} (Score {score})")
        return

    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev", # Sandbox domain
            "to": to_email,
            "subject": f"🔥 Lead Quente: {lead_name} (Score {score})",
            "html": f"""
                <h1>Novo Lead Quente!</h1>
                <p><strong>Nome:</strong> {lead_name}</p>
                <p><strong>WhatsApp:</strong> {lead_phone}</p>
                <p><strong>Score:</strong> {score}</p>
                <a href="https://app.funila.com.br/admin">Ver no Painel</a>
            """
        })
    except Exception as e:
        print(f"Error sending email: {e}")
