import threading
import time
from mistralai import Mistral
from openai import OpenAI
from httpx import Client
import logging

from config import API_KEY, API_GPT, PROXY


logger = logging.getLogger(__name__)


def mistral(message):
    logging.info('mistral')
    timeout = 60
    max_retries = 3
    base_delay = 5

    """Вызывает API Mistral с таймаутом и retry для ошибки 429."""
    client = Mistral(api_key=API_KEY)
    model_name = "mistral-medium-2505"

    result = [None]  # Используем список, чтобы изменить его внутри потока
    last_error = [None]

    def call_api():
        for attempt in range(max_retries):
            try:
                print(f"=== ПОПЫТКА {attempt + 1} ВЫЗОВА MISTRAL ===")
                response = client.chat.complete(
                    model=model_name,
                    messages=message
                )
                result[0] = response.choices[0].message.content
                print(f"=== MISTRAL УСПЕШНО ОТВЕТИЛ: {result[0]} ===")
                return
            except Exception as e:
                last_error[0] = e
                print(f"=== ОШИБКА MISTRAL (попытка {attempt + 1}): {e} ===")
                logging.debug(f"[Ошибка API mistral попытка {attempt + 1}] {e}")
                
                # Проверяем, это ли ошибка 429 (превышение лимита)
                if hasattr(e, 'status_code') and e.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Экспоненциальная задержка
                        print(f"=== ОШИБКА 429 - ЖДЕМ {delay} СЕКУНД ПЕРЕД ПОВТОРОМ ===")
                        logging.debug(f"Ошибка 429, ждем {delay} секунд перед повтором")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"=== ИСЧЕРПАНЫ ВСЕ ПОПЫТКИ ДЛЯ ОШИБКИ 429 ===")
                        logging.error("Исчерпаны все попытки для ошибки 429", exc_info=True)
                else:
                    print(f"=== ДРУГАЯ ОШИБКА - НЕ ПОВТОРЯЕМ ===")
                    logging.error("Произошла ошибка mistral", exc_info=True)
                    break

    thread = threading.Thread(target=call_api)
    thread.start()
    thread.join(timeout)  # Ждем `timeout` секунд

    if thread.is_alive():
        print("=== ТАЙМАУТ MISTRAL ===")
        return None

    time.sleep(1)
    final_result = str(result[0]) if result[0] else None
    print(f"=== ФИНАЛЬНЫЙ РЕЗУЛЬТАТ MISTRAL: {final_result} ===")
    return final_result


def gpt(message):
    logging.info('gpt')
    http_client = Client(proxy=PROXY)

    client = OpenAI(
        api_key=API_GPT,
        http_client=http_client
    )

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=message
    )

    return completion.choices[0].message.content