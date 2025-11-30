import pytest
import azure.functions as func
from azure_app.function_app import telegram_webhook, upload_file_handler, upload_ui
import json

def test_telegram_webhook_invalid(mock_env):
    req = func.HttpRequest(
        method='POST',
        body=json.dumps({}).encode('utf-8'),
        url='/api/telegram',
        params={}
    )
    resp = telegram_webhook(req)
    assert resp.status_code == 400

def test_upload_ui_missing_session(mock_env):
    req = func.HttpRequest(
        method='GET',
        body=None,
        url='/api/upload_ui',
        params={'mode': 'ui'}
    )
    resp = upload_ui(req)
    # Should fail without session
    assert resp.status_code == 400

def test_upload_ui_success(mock_env):
    req = func.HttpRequest(
        method='GET',
        body=None,
        url='/api/upload_ui',
        params={'mode': 'ui', 'session': '123'}
    )
    resp = upload_ui(req)
    assert resp.status_code == 200
    assert b"Upload File for Session 123" in resp.get_body()
