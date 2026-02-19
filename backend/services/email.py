import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY", "")

def send_lead_alert(to_email: str, lead_name: str, lead_phone: str, score: int):
    if not resend.api_key or "example" in resend.api_key:
        print(f"[Email Mock] Para: {to_email} | Lead: {lead_name} | Score: {score}")
        return
    try:
        resend.Emails.send({
            "from": "Funila <noreply@funila.com.br>",
            "to": to_email,
            "subject": f"Novo lead qualificado: {lead_name} (Score {score})",
            "html": f"""
            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:32px;">
                <h2 style="color:#2563EB;margin-bottom:8px;">Novo Lead Qualificado</h2>
                <p style="color:#6B7280;margin-bottom:24px;">Um lead com score alto acabou de preencher o formulário.</p>
                <table style="width:100%;border-collapse:collapse;">
                    <tr><td style="padding:12px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;">Nome</td>
                        <td style="padding:12px 0;border-bottom:1px solid #E5E7EB;font-weight:600;">{lead_name}</td></tr>
                    <tr><td style="padding:12px 0;border-bottom:1px solid #E5E7EB;color:#6B7280;">WhatsApp</td>
                        <td style="padding:12px 0;border-bottom:1px solid #E5E7EB;font-weight:600;">{lead_phone}</td></tr>
                    <tr><td style="padding:12px 0;color:#6B7280;">Score</td>
                        <td style="padding:12px 0;font-weight:600;color:#16A34A;">{score} pts</td></tr>
                </table>
                <a href="https://app.funila.com.br/frontend/admin/leads.html"
                   style="display:inline-block;margin-top:24px;padding:12px 24px;background:#2563EB;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">
                   Ver no painel
                </a>
            </div>
            """
        })
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
