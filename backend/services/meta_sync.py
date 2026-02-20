import httpx
from database import get_supabase
from utils.security import decrypt_aes256

async def sync_meta_account(client_id: str):
    supabase = get_supabase()

    # 1. Busca token
    acc_res = supabase.table('ad_accounts').select('*').eq('client_id', client_id).eq('platform', 'meta').execute()
    if not acc_res.data:
        return

    for acc in acc_res.data:
        token = decrypt_aes256(acc['access_token'])
        if not token: continue

        async with httpx.AsyncClient() as client:
            # 2. Busca contas de anuncio reais (sync accounts list)
            r = await client.get('https://graph.facebook.com/v19.0/me/adaccounts',
                params={'access_token': token, 'fields': 'id,name,currency,account_status'})

            if r.status_code != 200:
                print(f"Error syncing meta for {client_id}: {r.text}")
                continue

            accounts = r.json().get('data', [])

            for account in accounts:
                # Update ad_account table if needed (e.g. status)
                # For now we focus on campaigns

                # 3. Fetch Campaigns
                campaigns = await fetch_campaigns(account['id'], token, client)
                for camp in campaigns:
                    # Upsert Campaign
                    upsert_campaign(client_id, acc['id'], camp, supabase)

                    # 4. Fetch Creatives (Ads)
                    ads = await fetch_ads(account['id'], camp['id'], token, client)

                    for ad in ads:
                        upsert_creative(client_id, camp['id'], ad, supabase)

async def fetch_campaigns(account_id, token, client):
    r = await client.get(f'https://graph.facebook.com/v19.0/{account_id}/campaigns',
        params={'access_token': token, 'fields': 'id,name,status,objective,daily_budget'})
    return r.json().get('data', [])

def upsert_campaign(client_id, ad_account_uuid, camp_data, supabase):
    supabase.table('campaigns').upsert({
        'external_id': camp_data['id'],
        'client_id': client_id,
        'ad_account_id': ad_account_uuid,
        'name': camp_data.get('name'),
        'status': camp_data.get('status'),
        'objective': camp_data.get('objective'),
        'daily_budget_cents': int(camp_data.get('daily_budget', 0)) if camp_data.get('daily_budget') else 0
    }, on_conflict='external_id').execute()

async def fetch_ads(account_id, campaign_id, token, client):
    # fields: name, creative{thumbnail_url,title,body}, insights{spend,clicks,impressions,ctr}
    # Note: insights is a separate edge usually, or field expansion.
    # For ads endpoint, we can expand insights.
    fields = 'name,creative{thumbnail_url,title,body},insights{spend,clicks,impressions,ctr}'
    r = await client.get(f'https://graph.facebook.com/v19.0/{campaign_id}/ads',
        params={'access_token': token, 'fields': fields})
    return r.json().get('data', [])

def upsert_creative(client_id, campaign_external_id, ad_data, supabase):
    # Get campaign UUID
    camp_res = supabase.table('campaigns').select('id').eq('external_id', campaign_external_id).single().execute()
    if not camp_res.data:
        return

    camp_uuid = camp_res.data['id']

    insights_data = ad_data.get('insights', {})
    if isinstance(insights_data, dict) and 'data' in insights_data:
        insights = insights_data['data'][0] if insights_data['data'] else {}
    else:
        insights = {}

    creative_info = ad_data.get('creative', {})

    spend = float(insights.get('spend', 0))
    spend_cents = int(spend * 100)
    clicks = int(insights.get('clicks', 0))
    ctr = float(insights.get('ctr', 0))
    impressions = int(insights.get('impressions', 0))

    # Calculate leads generated (from leads table) to update creative metrics
    # Actually leads table has creative_id FK.
    # We should update `leads_generated` based on count of leads with this creative_id (if we link them).
    # But currently we don't link them yet (that's Google Sync or manually via UTM).
    # If leads have utm_content matching ad_data['id'] or name, we can link.
    # But for now, we just save what Meta tells us (Meta leads?) or 0.
    # The prompt says: "leads_generated INTEGER DEFAULT 0".
    # And "Rota GET /creatives... calcula score médio".
    # So we leave leads_generated as 0 or strictly from Meta (if using On-Facebook Leads).
    # But usually we want OUR leads.
    # I will leave it 0 here, relying on `leads` table aggregation for the frontend display.

    supabase.table('creatives').upsert({
        'external_id':   ad_data['id'],
        'client_id':     client_id,
        'campaign_id':   camp_uuid,
        'name':          ad_data.get('name', ''),
        'thumbnail_url': creative_info.get('thumbnail_url', ''),
        'headline':      creative_info.get('title', ''),
        'spend_cents':   spend_cents,
        'clicks':        clicks,
        'impressions':   impressions,
        'ctr':           ctr,
        'last_metrics_sync': 'NOW()'
    }, on_conflict='external_id').execute()
