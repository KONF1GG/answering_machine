from datetime import timedelta
import requests
import json
from connections import db_connextion
from functions.dadata import find_login, mistral, mistral_large
import time
import functions.action_functions as af


zapreshenka = ['start', 'stop', 'chat_closed', '/start', '/stop', '/chat_closed']

def login_application(mes):
    id_str = mes['id_str_sql']
    id_int = mes['id_int']
    chatBot = mes['chatBot']
    with requests.get(f'https://ws.freedom1.ru/redis/jivoid:{id_str}') as response:
        data = json.loads(json.loads(response.text))

    if 'login' in data:
        login = data['login']
        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'update ChatParameters set login_1c = "{login}" where id_int = "{id_int}" and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()

        return True
    return False


def is_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    sql = f'select login_ai, login_1c from ChatParameters where id_int = "{id_int}" and id_str = "{id_str}" and chat_bot = "{chatBot}"'
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(sql)
    row = cur.fetchone()
    db_connection.close()
    if row: 
        if row[0] not in ['', None] or row[1] not in ['', None]:
            return True
           
    if 'приложение' in chatBot:
        return login_application(mes)
    return False


def is_abon_info_mes(mes):
    text = mes['text']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    prompt_scheme = mes['prompt']
    prompt_name = 'first_identification'

    with requests.get(f'https://ws.freedom1.ru/redis/{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    prompt = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '')
    
    ans = mistral_large(text, prompt)
    if ans == 'Да':
        time.sleep(1)
        return find_login(mes)
        #добавить ^ сюда ретурны нормальные
    elif ans == 'Нет':
        return False
    elif len(ans) > 5 and len(ans) < 11:
        link = f'https://ws.freedom1.ru/redis/raw?query=ft.search%20idx:searchLogin%20%27{ans}%27'
        with requests.get(link) as responce:
            data = json.loads(responce.text)
        if data:
            login = list(data.keys())[0].split(':')[1]
            db_connection = db_connextion()
            cur = db_connection.cursor(buffered=True)
            cur.execute(f'update ChatParameters set login_ai = "{login}", step = "login_found" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()
            return True
    return False 


def is_physic(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    login = mes['login']
    messageId = mes['messageId']
    with requests.get(f'https://ws.freedom1.ru/redis/login:{login}') as response:
        try:
            data = json.loads(json.loads(response.text))
            if data['legal_entity']:
                ans = 'Передать диспетчеру'
                af.get_to_1c(id_str, id_int, chatBot, messageId, ans, '', 'юрик', mes['dt'])
                return False
            return True
        except TypeError as e:
            return True

    

def is_first_mes_on_day(mes):
    date = mes['dt']
    date = date - timedelta(hours=2)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    sql = f'select * from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and dt > "{dt}" and chat_bot = "{chatBot}"'
    cur.execute(sql)
    row = cur.fetchone()
    db_connection.close()
    if row:
        return False
    return True


def condition(mes, key):
        if key == 'is_login':
            return is_login(mes)
        elif key == 'is_abon_info_mes':
            return is_abon_info_mes(mes)
        elif key == 'is_physic':
            return is_physic(mes)
        elif key == 'is_first_mes_on_day':
            return is_first_mes_on_day(mes)
        else:
            print(f'Function {key} not found')
        return False

def start(key, mes, data):
    if not key or key == 'finish':
        return 'end'  # Возвращаем результат

    todo = data[key]['todo']
    if 'condition' in key:
    
        yes = data[key]['ifYes']
        no = data[key]['ifNo']

        if condition(mes, todo):
            return start(yes, mes, data)
        else:
            return start(no, mes, data)
    next_step = data[key]['next']
    if 'action' in key:
        
        if todo == 'empty':
            return start(next_step, mes, data)
        elif todo == 'get_login':
            new_mes = af.get_login(mes)
            if new_mes['login'] != 'Null':
                return start(next_step, new_mes, data)
            else:
                return start('finish', new_mes, data)
        else:
            eval(f'af.{todo}(mes)')
            return start(next_step, mes, data)

    return start(next_step, mes, data)