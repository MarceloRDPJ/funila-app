import httpx
import hashlib
import time
from database import get_supabase
from utils.security import decrypt_aes256

async def send_conversion_event(lead: dict, client_id: str):
    supabase = get_supabase()

    # 1. Fetch Meta Ad Account with Pixel ID
    acc_res = supabase.table('ad_accounts').select('*').eq('client_id', client_id).eq('platform', 'meta').execute()
    if not acc_res.data:
        return

    # Assuming first account found is the one to send event to
    acc = acc_res.data[0]
    pixel_id = acc.get('pixel_id')
    access_token_enc = acc.get('access_token')

    if not pixel_id or not access_token_enc:
        # If pixel_id is missing, maybe we can't send.
        return

    access_token = decrypt_aes256(access_token_enc)
    if not access_token: return

    phone_hash = hashlib.sha256(lead['phone'].encode()).hexdigest() if lead.get('phone') else None
    email_hash = hashlib.sha256(lead['email'].encode()).hexdigest() if lead.get('email') else None

    user_data = {
        'client_user_agent': lead.get('user_agent', ''),
    }
    if phone_hash: user_data['ph'] = [phone_hash]
    if email_hash: user_data['em'] = [email_hash]

    event = {
        'event_name': 'Purchase', # Or 'Lead'
        'event_time': int(time.time()),
        'user_data':  user_data,
        'custom_data': {
            'value':    1,
            'currency': 'BRL'
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f'https://graph.facebook.com/v19.0/{pixel_id}/events',
                params={'access_token': access_token},
                json={'data': [event]}
            )
            if r.status_code != 200:
                print(f"CAPI Error: {r.text}")
    except Exception as e:
        print(f"CAPI Exception: {e}")
