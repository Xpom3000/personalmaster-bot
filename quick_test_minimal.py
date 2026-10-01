import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
MODEL = "phi3:mini"

url = f"{OLLAMA_BASE_URL}/chat/completions"
# Самый простой запрос: только пользователь, без system-роли
payload = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "Привет. Сколько стоит маникюр с покрытием?"}
    ],
    "stream": False
}

print(f"✅ Отправляем запрос к {url}...")
try:
    # timeout=None — не обрываем запрос раньше времени
    with httpx.Client(timeout=None) as client:
        resp = client.post(url, json=payload)
        print(f"📡 Статус: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print("\n🗣 Ответ модели:")
            if data.get("choices") and len(data["choices"]) > 0:
                print(data["choices"][0]["message"]["content"])
            else:
                print("(Модель вернула пустой ответ)")
        else:
            print(f"\n⚠️ Неожиданный статус: {resp.status_code}")
            print("Тело ответа (ошибка от сервера):")
            print(resp.text)

except Exception as e:
    print(f"\n❌ Ошибка на стороне Python: {e}")
