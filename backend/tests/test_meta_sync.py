import sys
from unittest.mock import MagicMock, call

# Mock missing modules before importing the module under test
sys.modules['httpx'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['utils.security'] = MagicMock()
sys.modules['supabase'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.asyncio'] = MagicMock()

import pytest
from services.meta_sync import upsert_creative

def test_upsert_creative_success():
    supabase = MagicMock()
    mock_creatives_builder = MagicMock()

    def table_side_effect(table_name):
        if table_name == 'creatives':
            return mock_creatives_builder
        return MagicMock()

    supabase.table.side_effect = table_side_effect

    ad_data = {
        'id': 'ad-ext-123',
        'name': 'Test Ad',
        'creative': {
            'thumbnail_url': 'http://thumb.url',
            'title': 'Ad Title'
        },
        'insights': {
            'data': [{
                'spend': '10.50',
                'clicks': '100',
                'impressions': '1000',
                'ctr': '0.1'
            }]
        }
    }

    # Pass a valid UUID for campaign
    upsert_creative('client-1', 'camp-uuid-123', ad_data, supabase)

    # Verify upsert call
    supabase.table.assert_called_with('creatives')
    mock_creatives_builder.upsert.assert_called_once()

    upsert_arg = mock_creatives_builder.upsert.call_args[0][0]

    assert upsert_arg['external_id'] == 'ad-ext-123'
    assert upsert_arg['client_id'] == 'client-1'
    assert upsert_arg['campaign_id'] == 'camp-uuid-123'
    assert upsert_arg['name'] == 'Test Ad'
    assert upsert_arg['thumbnail_url'] == 'http://thumb.url'
    assert upsert_arg['headline'] == 'Ad Title'
    assert upsert_arg['spend_cents'] == 1050
    assert upsert_arg['clicks'] == 100
    assert upsert_arg['impressions'] == 1000
    assert upsert_arg['ctr'] == 0.1

def test_upsert_creative_no_campaign_uuid():
    supabase = MagicMock()

    # If camp_uuid is None, it should return early
    upsert_creative('client-1', None, {'id': 'ad-1'}, supabase)

    # Should not call table
    supabase.table.assert_not_called()

def test_upsert_creative_missing_insights():
    supabase = MagicMock()
    mock_creatives_builder = MagicMock()
    supabase.table.return_value = mock_creatives_builder

    ad_data = {
        'id': 'ad-ext-123',
        'name': 'Test Ad',
        'creative': {
            'thumbnail_url': 'http://thumb.url',
            'title': 'Ad Title'
        }
    }

    upsert_creative('client-1', 'camp-uuid-123', ad_data, supabase)

    upsert_arg = mock_creatives_builder.upsert.call_args[0][0]
    assert upsert_arg['spend_cents'] == 0
    assert upsert_arg['clicks'] == 0
    assert upsert_arg['impressions'] == 0
    assert upsert_arg['ctr'] == 0.0
