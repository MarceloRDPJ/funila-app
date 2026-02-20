from fastapi import APIRouter, Depends
from database import get_supabase
from dependencies import require_client

router = APIRouter(tags=["Creatives"])

@router.get('/creatives')
def get_creatives(user=Depends(require_client)):
    client_id = user['client_id']
    supabase = get_supabase()

    # Busca criativos
    # Include campaign name via join? Supabase select allows nested: *, campaign:campaigns(name)
    res = supabase.table('creatives').select('*, campaigns(name)').eq('client_id', client_id).execute()
    creatives = res.data

    # Para cada criativo, calcula score médio dos leads associados
    # Optimization: Perform one query for all leads of this client and aggregate in Python
    # instead of N queries.

    leads_res = supabase.table('leads').select('internal_score, creative_id, utm_content').eq('client_id', client_id).execute()
    leads = leads_res.data

    # Map leads by creative_id OR utm_content (external_id)
    leads_by_creative = {}

    for lead in leads:
        cid = lead.get('creative_id')
        utm = lead.get('utm_content')

        # We try to match by creative_id first
        if cid:
            if cid not in leads_by_creative: leads_by_creative[cid] = []
            leads_by_creative[cid].append(lead)

        # If not linked by ID, we could match by external_id (utm_content)
        # But for get_creatives loop, we iterate creatives which have ID and External ID.
        # So let's build a map of external_id -> creative_id to help matching?
        # Actually, let's just stick to what we have.

    for c in creatives:
        c_leads = leads_by_creative.get(c['id'], [])

        # Fallback: if 0 leads linked by ID, try matching by utm_content == external_id
        if not c_leads and c.get('external_id'):
             c_leads = [l for l in leads if l.get('utm_content') == c['external_id']]

        if c_leads:
            scores = [l['internal_score'] for l in c_leads if l.get('internal_score') is not None]
            avg_score = round(sum(scores) / len(scores)) if scores else 0
            c['avg_score'] = avg_score
            c['leads_generated'] = len(c_leads)
        else:
            c['avg_score'] = None
            c['leads_generated'] = 0

        # Flatten campaign name
        if c.get('campaigns'):
            c['campaign_name'] = c['campaigns'].get('name')
        else:
            c['campaign_name'] = None

    return {'creatives': creatives}
