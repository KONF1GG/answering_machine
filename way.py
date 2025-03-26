from datetime import timedelta
import requests
import json
from connections import db_connextion
from functions.dadata import find_login, mistral, mistral_large
import time
import functions.action_functions as af


zapreshenka = ['start', 'stop', 'chat_closed']
categoryes = ['Личный кабинет', 'Расторжение договора', 'Видеонаблюдение', 
            'Переезд', 'Подключение', 'Проверка скорости', 'Оборудование', 'Оплата', 'Тарифы', 'Телевидение', 
            'Баланс', 'Домофония', 'Повышение стоимости', 'Сервисный выезд', 'Отсутствие интернета', 'Приветствие']


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
    print(sql)
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(sql)
    row = cur.fetchone()
    db_connection.close()
    print(row)
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
    prompt = '''Определи есть ли в сообщении, написаном ниже, адрес или номер договора. 
                Номер договора это 6 цифр. Если есть адрес (обязательно должны быть населенный пункт, улица и дом) тогда напиши только 
                "Да", есть есть номер договора тогда напиши только его цифры и ничего кроме них.  Если  
                нет ни того ни другого тогда напиши "Нет". Сообщение:  '''
    

    ans = mistral_large(text, prompt)
    print(ans)
    if ans == 'Да':
        time.sleep(1)
        return find_login(mes)
        #добавить ^ сюда ретурны нормальные
    elif ans == 'Нет':
        return False
    elif len(ans) > 5 and len(ans) < 11:
        link = f'https://ws.freedom1.ru/redis/raw?query=ft.search%20idx:searchLogin%20%27{ans}%27'
        print(link)
        with requests.get(link) as responce:
            data = json.loads(responce.text)
        print(data)
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
    print(login)
    with requests.get(f'https://ws.freedom1.ru/redis/login:{login}') as response:
        try:
            data = json.loads(json.loads(response.text))
            print(data)
            if data['legal_entity']:
                ans = 'Передать диспетчеру'
                af.get_to_1c(id_str, id_int, chatBot, messageId, ans, '', 'юрик', mes['dt'])
                return False
            return True
        except TypeError as e:
            print(f"Error: {e}")
            print(f"Response text: {response.text}")
            return True

    

def is_first_mes_on_day(mes):
    date = mes['dt']
    date = date - timedelta(hours=2)
    print(date)
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
    print('###############################################################')
    print(sql)
    print('###############################################################')
    print(row)
    if row:
        return False
    return True


def is_new_category(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    text = mes['text']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    date = mes['dt']
    date = date - timedelta(hours=2)
    print(date)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'''select ChatStory.mes, ChatParameters.category from ChatStory join ChatParameters
                        on ChatStory.id_int = ChatParameters.id_int and ChatStory.id_str = ChatParameters.id_str
                        and ChatStory.chat_bot = ChatParameters.chat_bot
                        where ChatStory.dt > "{dt}" and ChatStory.id_int = {id_int}
                        and ChatStory.id_str = "{id_str}" and ChatStory.empl = 0 
                        and ChatParameters.chat_bot = "{chatBot}"''')
    row = cur.fetchall()
    db_connection.close()
    story = ''
    for result in row:
        story += f' {result[0]} '
    category = row[0][1]
    if category is None:
        af.category(mes)
        return False
    prompt = f'''
            Классифицируй категорию сообщения: "{text}" Предположительная категория: {category}?
            Предыдущие сообщения для понимания контекста: {story}
            Доступные категории: Личный кабинет, Расторжение договора, Видеонаблюдение, Переезд, Подключение, Проверка скорости,
            Оборудование, Оплата, Тарифы, Телевидение, Баланс, Домофония,
            Повышение стоимости, Сервисный выезд, Отсутствие интернета, Приветствие, Категория неопределена.
            Напиши только категорию, так же, как она написана здесь, соблюдая регистры и все прочее.
            Не работает тв это Телевидение. Не работает интернет это Отсутствие интернета, все вопросы, абсолютно, по балансу и оплате - это Баланс или Оплата. И так далее.
            Сообщение: 
            '''
    print(prompt)
    ans = mistral('', prompt)
    print(ans)

    db_connection = db_connextion()
    cursor_story = db_connection.cursor(buffered=True)
    cursor_story.execute(f'update ChatStory set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}" and messageId = "{messageId}"')
    db_connection.commit()
    db_connection.close()

    if ans in categoryes:
        db_connection = db_connextion()
        cursor = db_connection.cursor(buffered=True)
        cursor.execute(f'update ChatParameters set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()
        return True
    else:
        db_connection = db_connextion()
        cursor = db_connection.cursor(buffered=True)
        cursor.execute(f'update ChatParameters set category = "Неопределено" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()
        return False



def condition(mes, key):
        if key == 'is_new_category':
            return is_new_category(mes)
        elif key == 'is_login':
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
        print('end')
        return 'end'  # Возвращаем результат

    todo = data[key]['todo']
    print(todo)
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