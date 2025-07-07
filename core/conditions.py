from datetime import timedelta
import time
import json

import requests

from connections import execute_sql
from services.llm import mistral
from config import HTTP_REDIS#, ADDRESS_URL
import actions.action_functions as af

zapreshenka = ['start', 'stop', 'chat_closed', '/start', '/stop', '{"command":"start"}']

def login_application(mes):
    id_str = mes['id_str_sql']
    id_int = mes['id_int']
    chatBot = mes['chatBot']

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
        return True

    return False


def is_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    sql = """
        SELECT login_ai, login_1c 
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    row = execute_sql('select_one', sql, params)

    if row and (row[0] not in ['', None] or row[1] not in ['', None]):
        return True

    if 'приложение' in chatBot:
        return login_application(mes)

    return False


def is_abon_info_mes(mes):
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

    ans = mistral(story)

    '''if type(ans) == str:
        if ans == 'Да':
            time.sleep(1)
            story_text = af.all_mes_on_day(mes, sql=False, text=True) + mes['text']
            with requests.get(f'{ADDRESS_URL}adress?query={story_text}') as address_response:
                data_adsress = json.loads(address_response.text)
            if data_adsress['login']:
                login_serv_query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
                login_serv_params = (data_adsress['login'], id_int, id_str, chatBot)
                execute_sql('update', login_serv_query, login_serv_params)
                return True
            return False
        elif ans == 'Нет':
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
                return True'''

    return False


def is_physic(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    login = mes['login']
    messageId = mes['messageId']

    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        try:
            data = json.loads(json.loads(response.text))
            if data['legal_entity']:
                ans = 'Передать диспетчеру'
                af.get_to_1c(id_str, id_int, chatBot, messageId, ans, '', 'юрик', mes['dt'])
                return False
            return True
        except TypeError:
            return True


def is_first_mes_on_day(mes):
    date = mes['dt']
    dt = date - timedelta(hours=2)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    sql = """
        SELECT * FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND dt > %s AND chat_bot = %s
    """
    params = (id_int, id_str, dt, chatBot)
    row = execute_sql('select_one', sql, params)

    if row:
        return False

    return True