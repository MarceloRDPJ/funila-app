import sys
from unittest.mock import MagicMock

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
from unittest.mock import patch
from services.meta_sync import upsert_creative

def test_upsert_creative_campaign_not_found():
    supabase = MagicMock()
    # Mock campaign not found
    supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

    upsert_creative('client-1', 'camp-ext-1', {'id': 'ad-1'}, supabase)

    # Verify it checked the campaigns table
    supabase.table.assert_called_with('campaigns')
    # Verify it did not attempt to upsert to creatives
    creatives_called = any(call.args[0] == 'creatives' for call in supabase.table.call_args_list)
    assert not creatives_called

def test_upsert_creative_success_with_full_data():
    supabase = MagicMock()

    mock_campaign_builder = MagicMock()
    mock_creatives_builder = MagicMock()

    def table_side_effect(table_name):
        if table_name == 'campaigns':
            return mock_campaign_builder
        if table_name == 'creatives':
            return mock_creatives_builder
        return MagicMock()

    supabase.table.side_effect = table_side_effect

    # Mock campaign found
    mock_campaign_builder.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {'id': 'camp-uuid-123'}

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

    upsert_creative('client-1', 'camp-ext-1', ad_data, supabase)

    # Verify campaign lookup
    mock_campaign_builder.select.assert_called_with('id')

    # Verify upsert call
    mock_creatives_builder.upsert.assert_called_once()
    upsert_data = mock_creatives_builder.upsert.call_args[0][0]

    assert upsert_data['external_id'] == 'ad-ext-123'
    assert upsert_data['client_id'] == 'client-1'
    assert upsert_data['campaign_id'] == 'camp-uuid-123'
    assert upsert_data['name'] == 'Test Ad'
    assert upsert_data['thumbnail_url'] == 'http://thumb.url'
    assert upsert_data['headline'] == 'Ad Title'
    assert upsert_data['spend_cents'] == 1050
    assert upsert_data['clicks'] == 100
    assert upsert_data['impressions'] == 1000
    assert upsert_data['ctr'] == 0.1

def test_upsert_creative_missing_insights():
    supabase = MagicMock()
    mock_campaign_builder = MagicMock()
    mock_creatives_builder = MagicMock()

    def table_side_effect(table_name):
        if table_name == 'campaigns':
            return mock_campaign_builder
        if table_name == 'creatives':
            return mock_creatives_builder
        return MagicMock()

    supabase.table.side_effect = table_side_effect
    mock_campaign_builder.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {'id': 'camp-uuid-123'}

    ad_data = {
        'id': 'ad-ext-123',
        'name': 'Test Ad',
        'creative': {
            'thumbnail_url': 'http://thumb.url',
            'title': 'Ad Title'
        }
        # No insights
    }

    upsert_creative('client-1', 'camp-ext-1', ad_data, supabase)

    upsert_data = mock_creatives_builder.upsert.call_args[0][0]
    assert upsert_data['spend_cents'] == 0
    assert upsert_data['clicks'] == 0
    assert upsert_data['impressions'] == 0
    assert upsert_data['ctr'] == 0.0

def test_upsert_creative_empty_insights_data():
    supabase = MagicMock()
    mock_campaign_builder = MagicMock()
    mock_creatives_builder = MagicMock()

    def table_side_effect(table_name):
        if table_name == 'campaigns': return mock_campaign_builder
        if table_name == 'creatives': return mock_creatives_builder
        return MagicMock()

    supabase.table.side_effect = table_side_effect
    mock_campaign_builder.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {'id': 'camp-uuid-123'}

    ad_data = {
        'id': 'ad-ext-123',
        'insights': {
            'data': []
        }
    }

    upsert_creative('client-1', 'camp-ext-1', ad_data, supabase)

    upsert_data = mock_creatives_builder.upsert.call_args[0][0]
    assert upsert_data['spend_cents'] == 0
    assert upsert_data['clicks'] == 0

def test_upsert_creative_malformed_insights():
    supabase = MagicMock()
    mock_campaign_builder = MagicMock()
    mock_creatives_builder = MagicMock()

    def table_side_effect(table_name):
        if table_name == 'campaigns': return mock_campaign_builder
        if table_name == 'creatives': return mock_creatives_builder
        return MagicMock()

    supabase.table.side_effect = table_side_effect
    mock_campaign_builder.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {'id': 'camp-uuid-123'}

    ad_data = {
        'id': 'ad-ext-123',
        'insights': "not a dictionary"
    }

    upsert_creative('client-1', 'camp-ext-1', ad_data, supabase)

    upsert_data = mock_creatives_builder.upsert.call_args[0][0]
    assert upsert_data['spend_cents'] == 0
