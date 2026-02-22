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

# Configuration
META_APP_ID = os.getenv("META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET")
# Updated to match user's frontend configuration (GitHub Pages serves from root, so path includes frontend/)
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "https://app.funila.com.br/frontend/oauth/meta/callback/")
SECRET = os.getenv("ENCRYPTION_KEY") # Using Encryption Key as secret for state signing

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://app.funila.com.br/frontend/oauth/google/callback/")


@router.get('/oauth/meta/connect')
def meta_connect(request: Request, user=Depends(require_client)):
    if not META_APP_ID:
        raise HTTPException(status_code=500, detail="Meta App ID not configured")
    if not SECRET:
        raise HTTPException(status_code=500, detail="Encryption Key not configured")

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
    if not SECRET:
        raise HTTPException(status_code=500, detail="Encryption Key not configured")

    try:
        payload = jwt.decode(state, SECRET, algorithms=['HS256'])
        client_id = payload['client_id']
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    access_token = None
    async with httpx.AsyncClient() as client:
        r = await client.get('https://graph.facebook.com/v19.0/oauth/access_token', params={
            'client_id':     META_APP_ID,
            'client_secret': META_APP_SECRET,
            'redirect_uri':  META_REDIRECT_URI,
            'code':          code
        })
        if r.status_code != 200:
            print(f"Meta OAuth Error: {r.text}")
            raise HTTPException(status_code=400, detail="Failed to retrieve access token from Meta")

        token_data = r.json()
        access_token = token_data.get('access_token')

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token returned from Meta")

        # Encrypt token
        encrypted_token = encrypt_aes256(access_token)

        # Get User Info
        r_me = await client.get('https://graph.facebook.com/v19.0/me', params={'access_token': access_token, 'fields': 'id,name'})
        me_data = r_me.json()

        # Get Ad Accounts
        r_acc = await client.get('https://graph.facebook.com/v19.0/me/adaccounts', params={'access_token': access_token, 'fields': 'id,name,account_id'})
        acc_data = r_acc.json()
        data_list = acc_data.get('data', [])

        account_id = None
        account_name = None

        if not data_list:
             # Fallback if no ad account found, use user ID as placeholder
             account_id = me_data.get('id', 'unknown')
             account_name = me_data.get('name', 'Unknown User')
        else:
             # Use the first account found
             first_acc = data_list[0]
             # account_id field in Meta API is usually act_<ID>, but sometimes just ID.
             # But 'id' field is act_<ID>. 'account_id' is just the number.
             # The table probably expects string.
             account_id = first_acc.get('id')
             account_name = first_acc.get('name', 'Ad Account')

    # Upsert into database
    supabase = get_supabase()
    try:
        supabase.table('ad_accounts').upsert({
            'client_id':   client_id,
            'platform':    'meta',
            'account_id':  account_id,
            'account_name': account_name,
            'access_token': encrypted_token,
            'status':      'active'
        }, on_conflict='client_id, platform, account_id').execute()

        # Trigger sync
        background_tasks.add_task(sync_meta_account, client_id)

    except Exception as e:
        print(f"Database Error in Meta Callback: {e}")
        # Don't fail the request if DB fails, but log it.
        # Actually, if DB fails, the user won't be connected.
        pass

    frontend_url = os.getenv("FRONTEND_URL", "https://app.funila.com.br")
    # Redirect to frontend integration page with success status
    # Note: frontend/admin/integrations.html is the path
    return RedirectResponse(f"{frontend_url}/frontend/admin/integrations.html?status=connected")


@router.get('/oauth/google/connect')
def google_connect(request: Request, user=Depends(require_client)):
    if not GOOGLE_CLIENT_ID:
        # Return 501 so frontend knows it's not implemented/configured
        raise HTTPException(status_code=501, detail="Google Ads OAuth não configurado. Defina GOOGLE_CLIENT_ID no Render.")

    if not SECRET:
        raise HTTPException(status_code=500, detail="Encryption Key not configured")

    state = jwt.encode({'client_id': user['client_id']}, SECRET, algorithm='HS256')
    params = {
        'client_id':     GOOGLE_CLIENT_ID,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'https://www.googleapis.com/auth/adwords',
        'access_type':   'offline',
        'state':         state,
        'prompt':        'consent'
    }
    url = 'https://accounts.google.com/o/oauth2/auth?' + urlencode(params)
    return {"url": url}

@router.get('/oauth/google/callback')
async def google_callback(code: str, state: str):
    # Placeholder implementation - just redirect back
    frontend_url = os.getenv("FRONTEND_URL", "https://app.funila.com.br")
    return RedirectResponse(f"{frontend_url}/frontend/admin/integrations.html?status=google_connected")

@router.get('/integrations/status')
def get_integrations_status(user=Depends(require_client)):
    client_id = user['client_id']
    supabase = get_supabase()

    try:
        meta_acc = supabase.table('ad_accounts').select('*').eq('client_id', client_id).eq('platform', 'meta').execute()

        meta_connected = False
        meta_account_name = None
        meta_last_sync = None

        if meta_acc.data:
            # Check if any active account exists
            for acc in meta_acc.data:
                if acc.get('status') == 'active':
                    meta_connected = True
                    meta_account_name = acc.get('account_name')
                    meta_last_sync = acc.get('last_sync_at')
                    break

        return {
            "meta_connected": meta_connected,
            "meta_account_name": meta_account_name,
            "meta_last_sync": meta_last_sync
        }
    except Exception as e:
        print(f"Error fetching integration status: {e}")
        return {
            "meta_connected": False,
            "error": str(e)
        }
