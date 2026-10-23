import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="elion-test-", suffix=".db", delete=False)
_tmp.close()
os.environ["ELION_DATABASE_URL"] = "sqlite:///" + _tmp.name

import httpx
import pytest
from fastapi.testclient import TestClient

from database import Base, engine
from main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


class _Antwort:
    def __init__(self, inhalt: str, status: int = 200):
        self._inhalt = inhalt
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://localhost:11434/api/chat")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("Fehler", request=request, response=response)

    def json(self):
        return {"message": {"content": self._inhalt}}


@pytest.fixture
def ollama(monkeypatch):
    zustand = {"inhalt": "{}", "fehler": None, "payloads": [], "status": 200}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None):
            zustand["payloads"].append({"url": url, "json": json})
            if zustand["fehler"]:
                raise zustand["fehler"]
            return _Antwort(zustand["inhalt"], zustand["status"])

    monkeypatch.setattr("wrap.httpx.AsyncClient", FakeClient)
    return zustand
