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

    """Вызывает API Mistral с таймаутом."""
    client = Mistral(api_key=API_KEY)
    model_name = "mistral-medium-2505"


    result = [None]  # Используем список, чтобы изменить его внутри потока

    def call_api():
        try:
            response = client.chat.complete(
                model=model_name,
                messages=message
            )
            result[0] = response.choices[0].message.content
        except Exception as e:
            logging.debug(f"[Ошибка API mistral] {e}")
            logging.error("Произошла ошибка mistral", exc_info=True)

    thread = threading.Thread(target=call_api)
    thread.start()
    thread.join(timeout)  # Ждем `timeout` секунд

    if thread.is_alive():
        return None

    time.sleep(1)
    return str(result[0]) if result[0] else None


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