import json
import logging

import requests

from config import HTTP_VECTOR
from connections import execute_sql


logger = logging.getLogger(__name__)


def three_latest_messages(mes: dict):
    id_str = mes['id_str']
    id_int = mes['id_int']

    logging.info('three_latest_messages', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT mes FROM ChatStory
        WHERE id_str = %s
        AND id_int = %s
        AND empl = 0
        ORDER BY dt DESC
        LIMIT 3
    """
    params_db = (id_str, id_int)  # Правильный порядок!
    result = execute_sql('select_all', query, params_db)

    messages = [row[0] for row in result if row[0]]  # отбираем только непустые сообщения
    return ' '.join(messages[:3])

def getVector(text: str, mes: dict):
    query = three_latest_messages(mes)
    with requests.get(f'{HTTP_VECTOR}promt?query={query}') as response:
        data = json.loads(response.text)
    num = 0
    for row in data:
        if 'detail' in row:
            logging.info('В векторе нет стратей по теме')
            text += 'В базе нет инструкций для ответа на вопрос абонента. Если без этих инструкция данных для ответа недостаточно, то в ответе скажи только кодовую фразу "Передать диспетчеру".'
            return text
        else:
            text += '\n' + row['template']
            
    logging.info(f'Вектор отдал {num} статей.')
         
    return text
