from datetime import timedelta, datetime
import requests
import json
from connections import db_connextion
from functions.dadata import mistral
import functions.parametrs as params
import functions.text_prompt as text_prompt


def extract_words(text, login):
    import re
    words =  re.findall(r'<(.*?)>', text)

    #print(params)
    abon = params.Abonent(login)
    for word in words:
        value = eval(f'abon.{word}()')
        try:
            text = text.replace(f'<{word}>', str(value))
        except:
            text = text.replace(f'<{word}>', 'Неопознано')
    #print(text)
    return(text)


def get_to_1c(id, id_int, chatBot, messageId, ans, login, category, date):

    print('зашел')
    print(ans)

    if ans == 'Передать диспетчеру':
        dt = date.strftime('%Y-%m-%d %H:%M:%S')

        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'delete from ChatStory where id_int = {id_int} and id_str = "{id}" and chat_bot = "{chatBot}" and dt > "{dt}"')
        db_connection.commit()
        db_connection.close()

    if chatBot == 'Чат бот:Jivo Chat, токен:':
        send = True
        url = "http://192.168.111.61/UNF_FULL_WS/hs/chatmessanger/newmessage"
    else:
        send = True
        url = "http://server1c.freedom1.ru/UNF_CRM_WS/hs/chatmessanger/newmessage"

    if id_int == '0':
        post_ans = {"ChatBot":chatBot, 
                    "IDchat":str(id), 
                    "IDRecord":messageId,
                    "AIResponse":ans,
                    "Message":"Какое-то сообщение",
                    "RecordType":"12",
                    "SendFromBot": send,
                    "login": login,
                    "category": category,
                    "ContactUpdateData":"аа"}
    else:
        post_ans = {"ChatBot":chatBot, 
                    "IDchat":int(id_int), 
                    "IDRecord":messageId,
                    "AIResponse":ans,
                    "Message":"Какое-то сообщение",
                    "RecordType":"12",
                    "SendFromBot": send,
                    "login": login,
                    "category": category,
                    "ContactUpdateData":"аа"}
    print(post_ans)    
    

    try:
        response = requests.post(url, data=json.dumps(post_ans))
        response.raise_for_status()  # Вызывает исключение, если код ответа не 200
        print(response.status_code)
        print(response.text)
    except requests.RequestException as e:
        print(f"Ошибка при выполнении запроса: {e}")


def find_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select step, category, story from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()
    if row:
        if row[1]:
            category = row[1]
    else:
        category = ''
    if row:
        if category == 'Подключение':
            ans = 'Передать диспетчеру'
            get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

        elif row[0] not in ['login_search_mes_sent', 'login_search_mes_sent_1']:
            ans = 'Здравствуйте! Пожалуйста, уточните ваш адрес (включая населенный пункт) или номер договора.'
            get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

            db_connection = db_connextion()
            upd_cur = db_connection.cursor(buffered=True)
            upd_cur.execute(f'update ChatParameters set step = "login_search_mes_sent" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()
        
        elif row[0] == 'login_search_mes_sent':
            story = row[2]
            promt = f'''
                    Ты - специалист службы поддержки компании "Фридом", интернет-провайдера. И твоя задача сейчас распознать данные абонента для его корректной 
                    индентификации. Необходимые для этого данные: полный адрес, включая населенный пункт, улицу, дом и, если есть, квартиру. Или номер договора, 
                    который состоит из шести цифр. Будь вежливым и понимающим. Не здоровайся! Если не сможешь узнать данные абонента за два вопроса (именно два!), 
                    сообщи только кодовую фразу: "Передать диспетчеру". История общения с абонентом: {story}.
                    Сообщение, на которое ты должен ответить:               
                '''
            ans = mistral(promt, mes['text'])
            get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

            db_connection = db_connextion()
            upd_cur = db_connection.cursor(buffered=True)
            upd_cur.execute(f'update ChatParameters set step = "login_search_mes_sent_1" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()
        
        else:
            ans = 'Передать диспетчеру'
            get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

    return

def get_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    mes_dict = mes
    print(mes)
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select login_ai, login_1c from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()
    print(row)
    if row[0] not in ['', None]:
        print('11111111111111 ai')
        mes_dict['login'] = row[0]
    elif row[1] != '':
        print('222222222222222222222222222222222 1c')
        mes_dict['login'] = row[1]
    print('GET LOGIN!!!!!!!!!!!!!')
    print(mes_dict['login'])
    print(mes_dict)
    return mes_dict


def all_mes_on_day(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    date = mes['dt']
    date = date - timedelta(hours=2)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select mes, empl, dt from ChatStory where id_int = {id_int} and id_str = "{id_str}" and dt > "{dt}"  and chat_bot = "{chatBot}" order by dt')
    result = cur.fetchall()
    db_connection.close()
    
    text_chat = '\n\nИстория диалога: '
    for row in result:
        mesage = row[0]
        empl = row[1]

        if mesage == mes['text']:
            continue
        elif empl == 1:
            mesage = f'\nТы: {mesage}'
        elif empl == 0:
            mesage = f'\nАбонент: {mesage}'
        
        text_chat += mesage + ' '

    last_mes = mes['text']
    text_chat += f'\n Сообщение абонента, на которое ты должен ответить: {last_mes}'
    text_chat = text_chat.replace('"', '').replace("'", '').replace('Здравствуйте! Пожалуйста, уточните ваш адрес (включая населенный пункт) или номер договора.', '')

    db_connection = db_connextion()
    story_cur = db_connection.cursor(buffered=True)
    story_cur.execute(f'update ChatParameters set story = "{text_chat}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    db_connection.commit()
    db_connection.close()
    

def category(mes):
    categoryes = ['Личный кабинет', 'Расторжение договора', 'Видеонаблюдение', 
            'Переезд', 'Подключение', 'Проверка скорости', 'Оборудование', 'Оплата', 
            'Тарифы', 'Телевидение', 'Баланс', 'Домофония', 'Повышение стоимости', 
            'Сервисный выезд', 'Отсутствие интернета', 'Категория неопределена', 'Приветствие']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']

    date = mes['dt']
    date = date - timedelta(hours=1)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    prompt = '''Определи категорию обращения абонента по контексту его сообщения
            и укажи только её в ответе. Доступные категории: Личный кабинет,
            Расторжение договора, Видеонаблюдение, Переезд, Подключение, Проверка скорости,
            Оборудование, Оплата, Тарифы, Телевидение, Баланс, Домофония,
            Повышение стоимости, Сервисный выезд, Отсутствие интернета, Приветствие, Категория неопределена.
            Не работает тв это Телевидение. Не работает интернет это Отсутствие интернета, все вопросы, абсолютно, по балансу и оплате - это баланс и оплата. И так далее.
            Сообщение:  '''
    
    db_connection = db_connextion()

    last_mes = db_connection.cursor(buffered=True)
    last_mes.execute(f'select mes from ChatStory where id_str = "{id_str}" and id_int = {id_int} and dt > "{dt}" and messageId = "{messageId}"')
    result = last_mes.fetchall()
    text = ''
    for row in result:
        text += str(row[0]) + ' '

    ans = mistral(text, prompt)


    cursor_story = db_connection.cursor(buffered=True)
    cursor_story.execute(f'update ChatStory set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    db_connection.commit()
    db_connection.close()

    db_con = db_connextion()
    cur = db_con.cursor(buffered=True)
    if ans in categoryes:
        cur.execute(f'update ChatParameters set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_con.commit()
        db_con.close()
    else:
        cur.execute(f'update ChatParameters set category = "Неопределено" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_con.commit()
        db_con.close()


def prompt(mes):
    login = mes['login']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select category from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()
    
    category = row[0]

    if category in ['Баланс', 'Отсутствие интернета', 'Оплата', 'Аварии', 'Повышение стоимости', 'Тарифы']:
        if category == 'Баланс' or category == 'Оплата':
            schema = 'aibot_balance'
        elif category == 'Отсутствие интернета' or category == 'Аварии':
            schema = 'aibot_notinet'
        elif category == 'Повышение стоимости':
            schema = 'aibot_indexing'
        elif category == 'Тарифы':
            schema = 'aibot_tariffs'

        lzlzlz = text_prompt.Prompt(login, schema)
        text = lzlzlz.start('start', '')
        text_with_params = str(extract_words(text, login)).replace('"', '')
        text_with_params = text_with_params.replace("'", "")
        print('*************************************************************************')
        print(text_with_params)
        print('*************************************************************************')
        db_connection = db_connextion()
        prompt_cur = db_connection.cursor(buffered=True)
        prompt_cur.execute(f'update ChatParameters set prompt = "{text_with_params}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        print(f'update ChatParameters set prompt = "{text_with_params}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        db_connection.commit()
        db_connection.close()


def all_mes_category(mes):
    categoryes = ['Личный кабинет', 'Расторжение договора', 'Видеонаблюдение', 
            'Переезд', 'Подключение', 'Проверка скорости', 'Оборудование', 'Оплата', 
            'Тарифы', 'Телевидение', 'Баланс', 'Домофония', 'Повышение стоимости', 
            'Сервисный выезд', 'Отсутствие интернета', 'Категория неопределена', 'Приветствие']
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
    cur.execute(f'''select story, category from ChatParameters where id_int = {id_int}
                    and id_str = "{id_str}"  and chat_bot = "{chatBot}"''')
    row = cur.fetchone()
    print(f'''select story, category from ChatParameters where id_int = {id_int}
                    and id_str = "{id_str}"  and chat_bot = "{chatBot}"''')
    print('\nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
    print(row)
    print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n')
    db_connection.close()
    story = row[0]
    category = row[1]

    prompt = f'''
            Классифицируй категорию сообщения: "{text}" Предположительная категория: {category}?
            Предыдущие сообщения для понимания контекста: {story}
            Доступные категории: Личный кабинет, Расторжение договора, Видеонаблюдение, Переезд, Подключение, Проверка скорости,
            Оборудование, Оплата, Тарифы, Телевидение, Баланс, Домофония,
            Повышение стоимости, Сервисный выезд, Отсутствие интернета, Приветствие, Категория неопределена.
            Напиши только категорию, так же, как она написана здесь, соблюдая регистры и все прочее.
            Не работает тв это Телевидение. Не работает интернет это Отсутствие интернета, все вопросы, абсолютно, по балансу и оплате - это Баланс или Оплата. И так далее.
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
        cursor.execute(f'update ChatParameters set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}"  and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()
    else:
        db_connection = db_connextion()
        cursor = db_connection.cursor(buffered=True)
        cursor.execute(f'update ChatParameters set category = "Неопределено" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()

def non_category(mes):
    id_str = mes['id_str']
    id_int = mes['id_int']
    chatBot = mes['chatBot']

    db_connection = db_connextion()
    cur_find_step = db_connection.cursor()
    cur_find_step.execute(f'select step from ChatParameters where id_str = "{id_str}" and id_int = {id_int}  and chat_bot = "{chatBot}"')
    row = cur_find_step.fetchone()
    db_connection.close()

    if row[0] and 'non_category' in row[0]:
        if row[0] != 'non_category':
            dt = datetime.now()
            dt_str = dt.strftime('%d.%m.%Y %H:%M:%S')
            step_dt_str = row[0].split(';')[1]
            step_dt = datetime.strptime(step_dt_str, '%d.%m.%Y %H:%M:%S')
            difference = dt - step_dt
            hours_difference = difference.total_seconds() / 3600

            if hours_difference > 2:
                db_connection = db_connextion()
                cur_new_step = db_connection.cursor()
                cur_new_step.execute(f'update ChatParameters set step = "non_category;{dt_str}" where id_str = "{id_str}" and id_int = {id_int}  and chat_bot = "{chatBot}"')
                db_connection.commit()
                db_connection.close()

                return 'Какой у вас вопрос'

        else:
            db_connection = db_connextion()
            cur_new_step = db_connection.cursor()
            cur_new_step.execute(f'update ChatParameters set step = "disp" where id_str = "{id_str}" and id_int = {id_int}  and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()

            return 'Передать диспетчеру'
    
    else:
        dt_now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        db_connection = db_connextion()
        cur_new_step = db_connection.cursor()
        cur_new_step.execute(f'update ChatParameters set step = "non_category;{dt_now}" where id_str = "{id_str}" and id_int = {id_int}  and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()

        return 'Какой у вас вопрос'




def anser(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    login = mes['login']

    date = mes['dt']
    date = date - timedelta(hours=2)
    print(date)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select prompt, story, category from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and dt > "{dt}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()
    
    promt = f'{str(row[0])}, {str(row[1])}'
    category = row[2]
    if category in ['Баланс', 'Отсутствие интернета', 'Оплата', 'Аварии', 'Повышение стоимости', 'Тарифы'] and row[0] is not None:
        ans = mistral('', promt)
        if 'испетчер' in ans:
            ans = 'Передать диспетчеру'
        

        ans = ans.replace('Здравствуйте! ', '').replace('Здравствуйте. ', '').replace('Здравствуйте, ', '')
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
        print(ans)
    elif category in ['Баланс', 'Отсутствие интернета', 'Оплата', 'Аварии', 'Повышение стоимости', 'Тарифы'] and row[0] is None:
        prompt(mes)
        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'select prompt, story, category from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and dt > "{dt}" and chat_bot = "{chatBot}"')
        row = cur.fetchone()
        db_connection.close()   
        promt_new = f'{str(row[0])}, {str(row[1])}'
        ans = mistral('', promt_new)
        if 'испетчер' in ans:
            ans = 'Передать диспетчеру'
        ans = ans.replace('Здравствуйте! ', '').replace('Здравствуйте. ', '').replace('Здравствуйте, ', '').replace('Ты: ', '')
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
        print(ans) 
    elif category not in ['Баланс', 'Отсутствие интернета', 'Оплата', 'Аварии', 'Повышение стоимости', 'Тарифы', 'Приветствие', 'Категория неопределена']:    
        ans = 'Передать диспетчеру' 
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
        print(ans) 
    elif category in ['Приветствие', 'Категория неопределена']:
        ans = non_category(mes)
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    else:
        print(prompt)
        print(category)