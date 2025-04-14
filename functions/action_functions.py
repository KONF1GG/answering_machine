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
    

    try:
        response = requests.post(url, data=json.dumps(post_ans))
        response.raise_for_status()  # Вызывает исключение, если код ответа не 200
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
            prompt_name = 'support_identification'
            prompt_scheme = mes['prompt']

            with requests.get(f'https://ws.freedom1.ru/redis/{prompt_scheme}') as res:
                prompt_data = json.loads(json.loads(res.text))

            template = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '').replace('<', '{').replace('>', '}')
            promt = template.format(story=story)

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
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select login_ai, login_1c from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()

    if row[0] not in ['', None]:
        mes_dict['login'] = row[0]
    elif row[1] != '':
        mes_dict['login'] = row[1]
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
    category_connection = db_connextion()
    cur_category = category_connection.cursor(buffered=True)
    cur_category.execute('select category_name from category')
    result = cur_category.fetchall()
    category_connection.close()

    catergory_list = []

    for category_name in result:
        catergory_list.append(category_name[0])
    
    category_text = ', '.join(catergory_list)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']

    date = mes['dt']
    date = date - timedelta(hours=1)
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    prompt_name = 'first_category'
    prompt_scheme = mes['prompt']

    with requests.get(f'https://ws.freedom1.ru/redis/{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    template = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '').replace('<', '{').replace('>', '}')

    prompt = template.format(category_text=category_text)
    
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
    if ans in catergory_list:
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

    category_connecton = db_connextion()
    cur_category = category_connecton.cursor(buffered=True)
    cur_category.execute(f'select scheme, is_prompt from category where category_name = "{category}"')
    row_category = cur_category.fetchone()
    category_connecton.close()

    if row_category[1] == 1:
        schema = row_category[0]

        prompt = text_prompt.Prompt(login, schema, mes['text'])
        text = prompt.start('start', '')

        db_connection = db_connextion()
        prompt_cur = db_connection.cursor(buffered=True)

        if text == 'to_disp':
            prompt_cur.execute(f'update ChatParameters set prompt = "{text}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()   

        else:
            text_with_params = str(extract_words(text, login)).replace('"', '')
            text_with_params = text_with_params.replace("'", "")
            
            prompt_cur.execute(f'update ChatParameters set prompt = "{text_with_params}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
            db_connection.commit()
            db_connection.close()
            



def all_mes_category(mes):
    category_connection = db_connextion()
    cur_category = category_connection.cursor(buffered=True)
    cur_category.execute('select category_name from category')
    result = cur_category.fetchall()
    category_connection.close()

    catergory_list = []

    for category_name in result:
        catergory_list.append(category_name[0])
    
    category_text = ', '.join(catergory_list)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    text = mes['text']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    
    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'''select story, category from ChatParameters where id_int = {id_int}
                    and id_str = "{id_str}"  and chat_bot = "{chatBot}"''')
    row = cur.fetchone()
    db_connection.close()
    story = row[0]
    category = row[1]
    prompt_name = 'all_mes_category'
    prompt_scheme = mes['prompt']

    with requests.get(f'https://ws.freedom1.ru/redis/{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    template = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '').replace('<', '{').replace('>', '}')

    prompt = template.format(text=text, category=category, story=story, category_text=category_text)
    
    ans = mistral('', prompt)

    if ans == 'Категория неопределена':
        ans = category

    db_connection = db_connextion()
    cursor_story = db_connection.cursor(buffered=True)
    cursor_story.execute(f'update ChatStory set category = "{ans}" where id_int = {id_int} and id_str = "{id_str}" and messageId = "{messageId}"')
    db_connection.commit()
    db_connection.close()

    if ans in catergory_list:
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
    dt = date.strftime('%Y-%m-%d %H:%M:%S')

    db_connection = db_connextion()
    cur = db_connection.cursor(buffered=True)
    cur.execute(f'select prompt, story, category from ChatParameters where id_int = {id_int} and id_str = "{id_str}" and dt > "{dt}" and chat_bot = "{chatBot}"')
    row = cur.fetchone()
    db_connection.close()
    
    promt = f'{str(row[0])}, {str(row[1])}'
    category = row[2]

    category_connecton = db_connextion()
    cur_category = category_connecton.cursor(buffered=True)
    cur_category.execute(f'select is_prompt, is_active from category where category_name = "{category}"')
    row_category = cur_category.fetchone()
    category_connecton.close()
    is_prompt = row_category[0]
    is_active = row_category[1]

    if str(row[0]) == 'to_disp':
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])

    else:
        if is_prompt == 1 and is_active == 1 and row[0] is not None:
            ans = mistral('', promt)
            if 'испетчер' in ans:
                ans = 'Передать диспетчеру'
            
            ans = ans.replace('Здравствуйте! ', '').replace('Здравствуйте. ', '').replace('Здравствуйте, ', '')
            get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])

        elif is_prompt == 1 and is_active == 1 and row[0] is None:
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

        elif is_prompt == 0 and is_active == 0:    
            ans = 'Передать диспетчеру' 
            get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])

        elif is_prompt == 0 and is_active == 1:
            if category == 'Благодарность':
                ans = 'Рад помочь!'
            else:
                ans = non_category(mes)
            get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])