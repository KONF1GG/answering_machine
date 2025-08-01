import logging
import json
import requests

from config import HTTP_1C, HTTP_61
from connections import execute_sql

# Логгер
logger = logging.getLogger(__name__)


def get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, date):
    """
    Отправляет сообщение в 1С или Jivo. Если ans == 'Передать диспетчеру', удаляет запись из истории.

    Args:
        id_str (str): Строковый ID чата.
        id_int (str): Целочисленный ID чата или '0'.
        chatBot (str): Источник сообщения.
        messageId (str): ID сообщения.
        ans (str): Ответ от бота.
        login (str): Логин пользователя.
        category (str): Категория сообщения.
        date (datetime): Время для фильтрации при удалении.
    """
    logger.info('get_to_1c', extra={'id_str': id_str, 'id_int': id_int})

    if ans == 'Передать диспетчеру':
        query = """
            DELETE FROM ChatStory 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s AND dt > %s
        """
        params_db = (id_int, id_str, chatBot, date)
        try:
            execute_sql('delete', query, params_db)
            logger.debug('История удалена из-за передачи диспетчеру', extra={'id_str': id_str, 'id_int': id_int})
        except Exception as e:
            logger.error(f'Ошибка при удалении истории: {e}', extra={'id_str': id_str, 'id_int': id_int})

    # Определение URL
    if chatBot == 'Чат бот:Jivo Chat, токен:':
        url = f"{HTTP_61}hs/chatmessanger/newmessage"
    else:
        url = f"{HTTP_1C}hs/chatmessanger/newmessage"

    post_ans = {
        "ChatBot": chatBot,
        "IDchat": str(id_str) if id_int == '0' else int(id_int),
        "IDRecord": messageId,
        "AIResponse": ans,
        "Message": "Какое-то сообщение",
        "RecordType": "12",
        "SendFromBot": True,
        "login": login,
        "category": category,
        "ContactUpdateData": "аа"
    }

    try:
        response = requests.post(url, data=json.dumps(post_ans))
        response.raise_for_status()
        logger.info('Сообщение успешно отправлено в 1С/Jivo', extra={'id_str': id_str, 'id_int': id_int})
    except requests.RequestException as e:
        logger.error(f"Ошибка при выполнении запроса: {e}", extra={'id_str': id_str, 'id_int': id_int})