from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from database import get_supabase
from datetime import datetime, timedelta

router = APIRouter(tags=["Billing"])

def activate_subscription(asaas_sub_id: str):
    supabase = get_supabase()
    supabase.table('subscriptions').update({
        'status': 'active',
        'next_billing_at': (datetime.now() + timedelta(days=30)).isoformat()
    }).eq('asaas_sub_id', asaas_sub_id).execute()

def suspend_subscription(asaas_sub_id: str):
    supabase = get_supabase()
    supabase.table('subscriptions').update({'status': 'suspended'}).eq('asaas_sub_id', asaas_sub_id).execute()

def cancel_subscription(asaas_sub_id: str):
    supabase = get_supabase()
    supabase.table('subscriptions').update({'status': 'cancelled'}).eq('asaas_sub_id', asaas_sub_id).execute()

@router.post('/billing/webhook')
async def billing_webhook(payload: dict, background_tasks: BackgroundTasks):
    event = payload.get('event')
    # Asaas sends 'subscription' field with ID inside 'payment' or directly?
    # Usually payment.subscription

    # Simple logic based on prompt
    # Assuming payload has 'subscription' field which is the ID string?
    # Or object? Prompt says: activate_subscription(payload['subscription'])

    # Asaas Webhook:
    # { "event": "PAYMENT_CONFIRMED", "payment": { "subscription": "sub_123", ... } }

    sub_id = None
    if 'payment' in payload:
        sub_id = payload['payment'].get('subscription')
    elif 'subscription' in payload:
        if isinstance(payload['subscription'], dict):
            sub_id = payload['subscription'].get('id')
        else:
            sub_id = payload['subscription']

    if not sub_id:
        return {"ignored": True}

    if event == 'PAYMENT_CONFIRMED':
        background_tasks.add_task(activate_subscription, sub_id)
    elif event == 'PAYMENT_OVERDUE':
        background_tasks.add_task(suspend_subscription, sub_id)
    elif event == 'SUBSCRIPTION_DELETED' or event == 'SUBSCRIPTION_CANCELLED':
        background_tasks.add_task(cancel_subscription, sub_id)

    return {"received": True}
