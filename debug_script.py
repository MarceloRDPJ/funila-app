import httpx
import asyncio

async def test_api_calls():
    base_url = "http://localhost:8000" # Local mock or "https://funila-app.onrender.com" for remote
    # Since we can't easily mock the remote Supabase here, we will inspect the code logic instead.
    # The user provided curl commands are failing. Let's analyze the potential causes.
    # 1. /funnel/event failures?
    # 2. /leads/partial failures?
    # 3. /leads failures?

    # The curl commands show a flow:
    # 1. page_view (step 1)
    # 2. field_focus/blur (email, name, phone)
    # 3. leads/partial (save step 1) -> This is critical
    # 4. step_complete (step 1)
    # 5. step_complete (step 2) ?? wait, partial is step 1 end.
    # 6. field_focus/blur (cpf)
    # 7. leads (final submit)

    # Let's inspect backend/routes/links.py first as requested "analise e destrinche a parte da criacao do link ele ainda segue com erro"
    pass

if __name__ == "__main__":
    # Just a placeholder for now
    pass
