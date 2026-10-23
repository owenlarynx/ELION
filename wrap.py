import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"

async def pruefe_bericht(kind_info: str, rohtext: str) -> str:
    prompt = f"Prüfe diesen Tagesbericht knapp. Gib Hinweise und eine Ampel (Grün/Gelb/Rot).\n\nKind: {kind_info}\n\nBericht: {rohtext}"
    payload = {
        "model": "llama3.1",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(OLLAMA_URL, json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except Exception as e:
        return f"Prüfung nicht möglich (Ollama läuft nicht oder Fehler): {str(e)}"
