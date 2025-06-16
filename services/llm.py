import threading
import time
from mistralai import Mistral
#from openai import OpenAI
import httpx
import random

from config import API_KEY, API_GPT, PROXY

def mistral(message):
    """Вызывает API Mistral с таймаутом и несколькими попытками."""
    
    API_KEY = "YOUR_API_KEY"  # Убедись, что это определено или передаётся правильно
    model_name = "mistral-large-latest"
    timeout = 10
    retry_attempts = 2
    base_delay = 2  # Начальная задержка

    def call_api(result):
        try:
            client = Mistral(api_key=API_KEY)
            response = client.chat.complete(
                model=model_name,
                messages=message
            )
            result['response'] = response.choices[0].message.content
        except Exception as e:
            result['error'] = e
            print(f"Ошибка API: {e}")

    for attempt in range(retry_attempts):
        result = {'response': None, 'error': None}
        thread = threading.Thread(target=call_api, args=(result,))
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            print(f"[Попытка {attempt + 1}] Таймаут превышен. Прерываем...")
            # Прервать поток невозможно безопасно, но можно просто продолжить
        else:
            if result['response'] is not None:
                return str(result['response'])  # Успешный ответ

        # Если были ошибки — ждём перед следующей попыткой
        if attempt < retry_attempts - 1:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)  # Экспоненциальный backoff с jitter
            print(f"Ждём {delay:.2f} секунд перед повторной попыткой...")
            time.sleep(delay)

    # Если все попытки исчерпаны
    return 'Передать диспетчеру'


'''def gpt(message):

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
    return lala.content'''