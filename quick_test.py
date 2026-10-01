import requests
import json

OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
MODEL = "phi3:mini"

url = f"{OLLAMA_BASE_URL}/chat/completions"
payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Ты — консультант студии маникюра. Отвечай коротко, по делу."},
        {"role": "user", "content": "Сколько стоит маникюр с покрытием?"}
    ],
    "stream": False
}

print(f"✅ Отправляем запрос к {url}...")
try:
    resp = requests.post(url, json=payload, timeout=120)
    print(f"📡 Статус ответа: {resp.status_code}")
    data = resp.json()
    print("\n🗣 Ответ модели:")
    print(data["choices"][0]["message"]["content"])
except Exception as e:
    print(f"\n❌ Ошибка: {e}")
