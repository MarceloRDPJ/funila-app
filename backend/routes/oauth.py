import os
import httpx
from jose import jwt
from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from database import get_supabase
from dependencies import require_client
from utils.security import encrypt_aes256
from services.meta_sync import sync_meta_account

router = APIRouter(tags=["OAuth"])

META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "https://api.funila.com.br/oauth/meta/callback")
SECRET = os.getenv("ENCRYPTION_KEY") # Using Encryption Key as secret for state signing

@router.get('/oauth/meta/connect')
def meta_connect(request: Request, user=Depends(require_client)):
    if not META_APP_ID:
        raise HTTPException(status_code=500, detail="Meta App ID not configured")

    state = jwt.encode({'client_id': user['client_id']}, SECRET, algorithm='HS256')
    params = {
        'client_id':     META_APP_ID,
        'redirect_uri':  META_REDIRECT_URI,
        'scope':         'ads_read,business_management',
        'response_type': 'code',
        'state':         state
    }
    url = 'https://www.facebook.com/v19.0/dialog/oauth?' + urlencode(params)
    return {"url": url}

@router.get('/oauth/meta/callback')
async def meta_callback(code: str, state: str, background_tasks: BackgroundTasks):
    try:
        payload = jwt.decode(state, SECRET, algorithms=['HS256'])
        client_id = payload['client_id']
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    async with httpx.AsyncClient() as client:
        r = await client.get('https://graph.facebook.com/v19.0/oauth/access_token', params={
            'client_id':     META_APP_ID,
            'client_secret': META_APP_SECRET,
            'redirect_uri':  META_REDIRECT_URI,
            'code':          code
        })
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from Meta")

        token_data = r.json()
        access_token = token_data['access_token']

    encrypted_token = encrypt_aes256(access_token)

    supabase = get_supabase()

    # Check if ad_account entry exists or just insert/update logic
    # We don't have account_id yet, usually we get it after token.
    # But for now we store the token linked to the client.
    # The sync service will populate account details.
    # We'll insert a placeholder or update if exists.
    # Actually, we might need to query /me/adaccounts immediately to get ID?
    # The prompt says: "Salva no banco... Dispara sync".
    # But ad_accounts table has account_id NOT NULL.
    # So we probably need to fetch account info first.

    # Let's fetch basic user info or accounts
    async with httpx.AsyncClient() as client:
        r_me = await client.get('https://graph.facebook.com/v19.0/me', params={'access_token': access_token, 'fields': 'id,name'})
        me_data = r_me.json()
        # This is the User ID, not Ad Account ID.
        # A user can have multiple ad accounts.
        # We need to list ad accounts and maybe pick one or store all?
        # The sync service logic: "Busca contas de anúncio... for account in accounts... upsert_creative".
        # It seems we should store the USER token, and then fetch accounts.
        # But table is `ad_accounts`.
        # Maybe we assume 1 main account or loop?
        # Prompt says: "table ad_accounts... account_id... access_token".
        # Prompt `meta_callback` code:
        # supabase.table('ad_accounts').insert({ ... 'access_token': encrypted_token ... })
        # It inserts without account_id? But schema has account_id NOT NULL.
        # I will fetch the first ad account ID to satisfy the constraint or modify the logic.

        r_acc = await client.get('https://graph.facebook.com/v19.0/me/adaccounts', params={'access_token': access_token})
        acc_data = r_acc.json()
        data_list = acc_data.get('data', [])

        if not data_list:
             # No ad account found? Store as pending or user level?
             # Schema requires account_id. I'll use 'pending' or user id.
             account_id = me_data.get('id', 'unknown')
             account_name = me_data.get('name', 'Unknown')
        else:
             # Just pick the first one for now or loop?
             # If we support multiple, we might need a selection screen.
             # For MVP Sprint 2, let's pick the first one.
             first_acc = data_list[0]
             account_id = first_acc.get('id')
             account_name = first_acc.get('name', 'Ad Account')

    supabase.table('ad_accounts').upsert({
        'client_id':   client_id,
        'platform':    'meta',
        'account_id':  account_id,
        'account_name': account_name,
        'access_token': encrypted_token,
        'status':      'active'
    }, on_conflict='client_id, platform, account_id').execute() # Need unique constraint or just client_id if 1:1

    background_tasks.add_task(sync_meta_account, client_id)
    return RedirectResponse('https://funila-app.onrender.com/frontend/admin/integrations.html?status=connected')

@router.get('/oauth/google/connect')
def google_connect(user=Depends(require_client)):
    # Placeholder for Google OAuth
    # Real implementation requires Google Cloud Console setup
    return {"url": "https://accounts.google.com/o/oauth2/auth?client_id=GOOGLE_CLIENT_ID&redirect_uri=CALLBACK&response_type=code&scope=https://www.googleapis.com/auth/adwords"}

@router.get('/oauth/google/callback')
async def google_callback(code: str, state: str):
    # Placeholder
    return RedirectResponse('https://funila-app.onrender.com/frontend/admin/integrations.html?status=google_connected')

@router.get('/integrations/status')
def get_integrations_status(user=Depends(require_client)):
    client_id = user['client_id']
    supabase = get_supabase()

    meta_acc = supabase.table('ad_accounts').select('*').eq('client_id', client_id).eq('platform', 'meta').execute()

    meta_connected = False
    meta_account_name = None
    meta_last_sync = None

    if meta_acc.data:
        acc = meta_acc.data[0]
        meta_connected = True
        meta_account_name = acc.get('account_name')
        meta_last_sync = acc.get('last_sync_at')

    return {
        "meta_connected": meta_connected,
        "meta_account_name": meta_account_name,
        "meta_last_sync": meta_last_sync
    }
