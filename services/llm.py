import threading
import time
from mistralai import Mistral
from openai import OpenAI
import httpx

from config import API_KEY, API_GPT, PROXY

def mistral(message):

    timeout = 60

    """Вызывает API Mistral с таймаутом."""
    client = Mistral(api_key=API_KEY)
    model_name = "mistral-large-latest"


    result = [None]  # Используем список, чтобы изменить его внутри потока

    def call_api():
        try:
            response = client.chat.complete(
                model=model_name,
                messages=message
            )
            result[0] = response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка API: {e}")

    thread = threading.Thread(target=call_api)
    thread.start()
    thread.join(timeout)  # Ждем `timeout` секунд

    if thread.is_alive():
        return None

    time.sleep(1)
    return str(result[0]) if result[0] else None


def gpt(message):

    # Настройка прокси
    proxy = PROXY  # Замените на адрес вашего прокси
    proxies = {
        "http://": proxy,
        "https://": proxy,
    }

    # Создаем HTTP-клиент с поддержкой прокси
    http_client = httpx.Client(proxies=proxies)

    client = OpenAI(
    api_key=API_GPT,
    http_client=http_client
    )

    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    store=True,
    messages=message
    )
    lala = completion.choices[0].message
    return lala.content