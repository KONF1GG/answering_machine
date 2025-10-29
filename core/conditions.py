import logging
from datetime import timedelta
import time
import json

import requests

from connections import execute_sql
from services.llm import gpt
from config import HTTP_REDIS, HTTP_ADDRESS
import actions.action_functions as af

# Логгер
logger = logging.getLogger(__name__)

zapreshenka = ['start', 'stop', 'chat_closed', '/start', '/stop', '{"command":"start"}']


def login_application(mes):
    logger.info('login_application', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    id_str = mes['id_str_sql']
    id_int = mes['id_int']
    chatBot = mes['chatBot']

    try:
        with requests.get(f'{HTTP_REDIS}jivoid:{id_str}') as response:
            data = json.loads(json.loads(response.text))

        if 'login' in data:
            login = data['login']
            query = """
                UPDATE ChatParameters 
                SET login_1c = %s 
                WHERE id_int = %s AND id_str = %s AND chat_bot = %s
            """
            params = (login, id_int, id_str, chatBot)
            execute_sql('update', query, params)
            logger.debug('Логин из приложения обновлён', extra={'id_str': id_str, 'id_int': id_int})
            return True

        logger.debug('Логин из приложения не найден', extra={'id_str': id_str, 'id_int': id_int})
        return False
    except Exception as e:
        logger.error(f'Ошибка в login_application: {e}', extra={'id_str': id_str, 'id_int': id_int})
        return False


def is_login(mes):
    logger.info('is_login', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    try:
        sql = """
            SELECT login_ai, login_1c 
            FROM ChatParameters 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        params = (id_int, id_str, chatBot)
        row = execute_sql('select_one', sql, params)

        if row and (row[0] not in ['', None] or row[1] not in ['', None]):
            logger.debug('Логин уже существует', extra={'id_str': id_str, 'id_int': id_int})
            return True

        if 'приложение' in chatBot:
            logger.debug('Попытка входа через приложение', extra={'id_str': id_str, 'id_int': id_int})
            return login_application(mes)

        logger.debug('Логин не найден', extra={'id_str': id_str, 'id_int': id_int})
        return False
    except Exception as e:
        logger.error(f'Ошибка в is_login: {e}', extra={'id_str': id_str, 'id_int': id_int})
        return False


def is_abon_info_mes(mes):
    logger.info('is_abon_info_mes', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    prompt_scheme = mes['prompt']
    prompt_name = 'first_identification'

    try:
        with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
            prompt_data = json.loads(json.loads(res.text))

        prompt = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '')
        story = af.all_mes_on_day(mes, sql=False)
        promt_mes = {"role": "system", "content": prompt}
        story.insert(0, promt_mes)

        ans = gpt(story)

        if type(ans) == str:
            if ans == 'Да':
                logger.debug('Mistral: "Да", пытаемся получить адрес', extra={'id_str': id_str, 'id_int': id_int})
                time.sleep(1)
                story_text = af.all_mes_on_day(mes, sql=False, text=True) + mes['text']
                with requests.get(f'{HTTP_ADDRESS}adress?query={story_text}') as address_response:
                    data_adsress = json.loads(address_response.text)
                if data_adsress['login']:
                    login_serv_query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
                    login_serv_params = (data_adsress['login'], id_int, id_str, chatBot)
                    execute_sql('update', login_serv_query, login_serv_params)
                    logger.info('Логин установлен через адрес', extra={'id_str': id_str, 'id_int': id_int})
                    return True
                logger.debug('Логин через адрес не найден', extra={'id_str': id_str, 'id_int': id_int})
                return False
            elif ans == 'Нет':
                logger.debug('Mistral: "Нет"', extra={'id_str': id_str, 'id_int': id_int})
                return False
            elif 5 < len(ans) < 11:
                link = f'{HTTP_REDIS}raw?query=ft.search%20idx:searchLogin%20%27{ans}%27'
                with requests.get(link) as responce:
                    data = json.loads(responce.text)

                if data:
                    login = list(data.keys())[0].split(':')[1]
                    query = """
                        UPDATE ChatParameters 
                        SET login_ai = %s, step = "login_found" 
                        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
                    """
                    params = (login, id_int, id_str, chatBot)
                    execute_sql('update', query, params)
                    logger.info(f'Логин найден через поиск: {login}', extra={'id_str': id_str, 'id_int': id_int})
                    return True

        logger.debug('Неожиданный ответ от Mistral или совпадений не найдено', extra={'id_str': id_str, 'id_int': id_int})
        return False
    except Exception as e:
        logger.error(f'Ошибка в is_abon_info_mes: {e}', extra={'id_str': id_str, 'id_int': id_int})
        return False


def is_physic(mes):
    logger.info('is_physic', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    login = mes['login']
    messageId = mes['messageId']

    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as response:
            data = json.loads(json.loads(response.text))
            if data['legal_entity']:
                ans = 'Передать диспетчеру'
                af.get_to_1c(id_str, id_int, chatBot, messageId, ans, '', 'юрик', mes['dt'])
                logger.info('Юридическое лицо, сообщение передано диспетчеру', extra={'id_str': id_str, 'id_int': id_int})
                return False
            logger.debug('Физическое лицо', extra={'id_str': id_str, 'id_int': id_int})
            return True
    except TypeError:
        logger.warning('Ошибка типа при проверке юрлица, предполагаем физлицо', extra={'id_str': id_str, 'id_int': id_int})
        return True
    except Exception as e:
        logger.error(f'Ошибка в is_physic: {e}', extra={'id_str': id_str, 'id_int': id_int})
        return True


def is_first_mes_on_day(mes):
    logger.info('is_first_mes_on_day', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    date = mes['dt']
    dt = date - timedelta(hours=2)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    try:
        sql = """
            SELECT * FROM ChatParameters 
            WHERE id_int = %s AND id_str = %s AND dt > %s AND chat_bot = %s
        """
        params = (id_int, id_str, dt, chatBot)
        row = execute_sql('select_one', sql, params)

        if row:
            logger.debug('Это не первое сообщение дня', extra={'id_str': id_str, 'id_int': id_int})
            return False

        logger.info('Это первое сообщение дня', extra={'id_str': id_str, 'id_int': id_int})
        return True
    except Exception as e:
        logger.error(f'Ошибка в is_first_mes_on_day: {e}', extra={'id_str': id_str, 'id_int': id_int})
        return False
    

def is_connection(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    sql = """
        SELECT category FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    row = execute_sql('select_one', sql, params)
    
    if is_login(mes):
        return False 
    
    if row and row[0] == 'Подключение':
        return True

    return False


def is_houseId(mes):
    id_int = mes['id_int']
    id_str = mes['id_str']
    chatBot = mes['chatBot']

    sql = """
        SELECT address_info
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    row = execute_sql('select_one', sql, params)

    if row and row[0] not in ['', None]:
        address_info = json.loads(row[0])

        if 'houseid' in address_info and address_info['houseid'] is not None:
            return True

    return False



def is_address_info_mes(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    prompt_scheme = mes['prompt']
    prompt_name = 'first_identification'

    with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    prompt = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '')
    story = af.all_mes_on_day(mes, sql=False)
    promt_mes = {"role": "system", "content": prompt}
    story.insert(0, promt_mes)

    ans = gpt(story)

    if type(ans) == str:
        if ans in ['Да', 'Да.', 'да', 'да.']:
            time.sleep(1)
            story_text = af.all_mes_on_day(mes, sql=False, text=True) + mes['text']
            with requests.get(f'{HTTP_ADDRESS}adress?query={story_text}') as address_response:
                data_adsress = json.loads(address_response.text)
            if data_adsress:
                login_serv_query = 'update ChatParameters set address_info = %s where id_int = %s and id_str = %s and chat_bot = %s'
                login_serv_params = (str(data_adsress).replace("'", '"').replace('None', 'null'), id_int, id_str, chatBot)
                execute_sql('update', login_serv_query, login_serv_params)
                return True
            return False

    return False


def is_contype(mes):
    houseid = mes['login']
    with requests.get(f'{HTTP_REDIS}adds:{houseid}') as response:
        if response.text != 'false':
            house_data = json.loads(json.loads(response.text))
        else:
            house_data = {'conn_type': []}

    if house_data['conn_type'] != []:
        return True

    return False