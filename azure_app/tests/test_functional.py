import pytest
import azure.functions as func
from azure_app.function_app import telegram_webhook, upload_file_handler, upload_ui, UploadHandler
import json
from unittest.mock import MagicMock, patch

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

def test_upload_file_handler_multipart(mock_env, monkeypatch):
    # Mock UploadHandler.handle to avoid external calls
    mock_handle = MagicMock(return_value="<html>Success</html>")
    monkeypatch.setattr("azure_app.function_app.UploadHandler.handle", mock_handle)

    # Construct manual multipart body
    boundary = "boundary123"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "Hello World\r\n"
        f"--{boundary}--\r\n"
    ).encode('utf-8')

    req = func.HttpRequest(
        method='POST',
        body=body,
        url='/api/upload_file',
        params={'session': 'session_123'},
        headers={'Content-Type': f'multipart/form-data; boundary="{boundary}"'}
    )

    resp = upload_file_handler(req)

    assert resp.status_code == 200
    assert b"<html>Success</html>" in resp.get_body()

    # Verify handle was called with correct args
    mock_handle.assert_called_once()
    args = mock_handle.call_args[0]
    assert args[0] == 'session_123' # session_id
    assert args[1] == b'Hello World' # file_data
    assert args[2] == 'test.txt' # filename
    assert args[3] == 'text/plain' # content_type
