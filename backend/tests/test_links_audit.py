import sys
from unittest.mock import MagicMock

# Mock required modules
sys.modules['database'] = MagicMock()
sys.modules['dependencies'] = MagicMock()
sys.modules['supabase'] = MagicMock()

import pytest
from unittest.mock import patch, call
from routes.links import create_link, LinkCreate, HTTPException

def test_create_link_success():
    with patch('routes.links.get_supabase') as mock_get_supabase:
        supabase = MagicMock()
        mock_get_supabase.return_value = supabase

        # Mock table('links')
        mock_table = MagicMock()
        supabase.table.return_value = mock_table

        # Mock select().eq().execute().data -> [] (no collision)
        mock_select = mock_table.select.return_value
        mock_eq = mock_select.eq.return_value
        mock_exec = mock_eq.execute.return_value
        mock_exec.data = []

        # Mock insert().execute().data -> [{'id': '123'}]
        mock_insert = mock_table.insert.return_value
        mock_insert_exec = mock_insert.execute.return_value
        mock_insert_exec.data = [{'id': '123', 'slug': 'test-link', 'client_id': 'client-1'}]

        user_profile = {'client_id': 'client-1', 'role': 'client'}
        link_data = LinkCreate(name="Test Link", destination="http://dest.com")

        result = create_link(link_data, user_profile)

        assert result['id'] == '123'

        # Verify slug generation logic
        # Should check collision for 'test-link'
        supabase.table.assert_any_call('links')
        mock_table.select.assert_called() # checks collision

        # Verify insert
        mock_table.insert.assert_called()
        insert_args = mock_table.insert.call_args[0][0]
        assert insert_args['name'] == 'Test Link'
        assert insert_args['client_id'] == 'client-1'
        assert 'slug' in insert_args

def test_create_link_capture_without_url():
    with patch('routes.links.get_supabase') as mock_get_supabase:
        supabase = MagicMock()
        mock_get_supabase.return_value = supabase

        user_profile = {'client_id': 'client-1'}
        # Capture mode requires capture_url
        link_data = LinkCreate(name="Test", destination="http://dest.com", funnel_type="capture")

        with pytest.raises(HTTPException) as exc:
            create_link(link_data, user_profile)
        assert exc.value.status_code == 400

def test_create_link_db_error():
    with patch('routes.links.get_supabase') as mock_get_supabase:
        supabase = MagicMock()
        mock_get_supabase.return_value = supabase

        mock_table = MagicMock()
        supabase.table.return_value = mock_table

        # Slug check passes
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        # Insert raises exception
        mock_table.insert.side_effect = Exception("DB Error")

        user_profile = {'client_id': 'client-1'}
        link_data = LinkCreate(name="Test", destination="http://dest.com")

        with pytest.raises(HTTPException) as exc:
            create_link(link_data, user_profile)
        assert exc.value.status_code == 500
