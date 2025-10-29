from datetime import datetime, timedelta
import time
import json
import logging

import requests

from config import HTTP_REDIS
from connections import execute_sql
from services.llm import gpt
from prompts.extract_words import extract_words, extract_connection_words
from services.get_to_1c import get_to_1c
from actions.management import non_category
import prompts.text_prompt as text_prompt


logger = logging.getLogger(__name__)


def all_mes_on_day(mes, sql=True, text=False):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    date = mes['dt']
    dt = date - timedelta(hours=2)

    logging.info('all_mes_on_day', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT mes, empl, dt 
        FROM ChatStory 
        WHERE id_int = %s AND id_str = %s AND dt > %s AND chat_bot = %s 
        ORDER BY dt
    """
    params_db = (id_int, id_str, dt, chatBot)
    result = execute_sql('select_all', query, params_db)

    list_chat = []
    text_chat = '\nИстория диалога: '
    for row in result:
        message_text = row[0]
        empl = row[1]

        if message_text == mes['text'] or message_text == (
            'Здравствуйте! Пожалуйста, уточните ваш адрес '
            '(включая населенный пункт) или номер договора.'
        ):
            continue

        if empl == 1:
            list_chat.append({"role": "assistant", "content": message_text})
            text_chat += f'\nТы: {message_text}'
        else:
            list_chat.append({"role": "user", "content": message_text})
            text_chat += f'\nАбонент: {message_text}'

    last_mes = mes['text']
    list_chat.append({"role": "user", "content": last_mes})

    if text:
        logging.info('Текстовая история', extra={'id_str':id_str, 'id_int':id_int})
        return text_chat
    elif not sql:
        logging.info('История List', extra={'id_str':id_str, 'id_int':id_int})
        return list_chat

    sql_text = str(list_chat).replace('"', '\"')
    if sql:
        logging.info('Запись истории в sql', extra={'id_str':id_str, 'id_int':id_int})
        update_query = """
            UPDATE ChatParameters 
            SET story = %s 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        update_params = (sql_text, id_int, id_str, chatBot)
        execute_sql('update', update_query, update_params)


def find_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']

    logging.info('find_login', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT step, category, story 
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params_db = (id_int, id_str, chatBot)
    row = execute_sql('select_one', query, params_db)

    category = row[1] if row and row[1] else ''

    if row and category == 'Подключение':
        logging.info('Подключение', extra={'id_str':id_str, 'id_int':id_int})
        return 'Подключение'
    elif row and row[0] not in ['login_search_mes_sent', 'login_search_mes_sent_1']:
        logging.info('Первая попытка найти адрес', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Здравствуйте! Пожалуйста, уточните ваш адрес (включая населенный пункт) или номер договора.'
        get_to_1c(
            id_str, id_int, chatBot, messageId, ans, '', category, mes['dt']
        )
        upd_query = """
            UPDATE ChatParameters 
            SET step = "login_search_mes_sent" 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        upd_params = (id_int, id_str, chatBot)
        execute_sql('update', upd_query, upd_params)
    elif row and row[0] == 'login_search_mes_sent':
        logging.info('Вторая попытка найти адрес', extra={'id_str':id_str, 'id_int':id_int})
        prompt_name = 'support_identification'
        prompt_scheme = mes['prompt']

        with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
            prompt_data = json.loads(json.loads(res.text))

        template = next(
            (d['template'] for d in prompt_data if d['name'] == prompt_name), ''
        ).replace('<', '{').replace('>', '}')

        story = all_mes_on_day(mes, sql=False, text=True)
        prompt = template.format(category=category, story=story)
        gpt_prompt = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": mes['text']}
        ]
        ans = gpt(gpt_prompt)
        get_to_1c(
            id_str, id_int, chatBot, messageId, ans, '', category, mes['dt']
        )

        upd_query = """
            UPDATE ChatParameters 
            SET step = "login_search_mes_sent_1" 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        upd_params = (id_int, id_str, chatBot)
        execute_sql('update', upd_query, upd_params)
    elif row:
        logging.info('Адрес не найден, отдаем диспу', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

    return


def get_login(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    logging.info('get_login', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT login_ai, login_1c 
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params_db = (id_int, id_str, chatBot)
    row = execute_sql('select_one', query, params_db)

    mes_dict = mes.copy()

    if row[0] not in ['', None]:
        login = row[0]
        logging.info(f'Перезаписан словарь mes, логин = {login}', extra={'id_str':id_str, 'id_int':id_int})
        mes_dict['login'] = login
    elif row[1] not in ['', None]:
        login = row[1]
        logging.info(f'Перезаписан словарь mes, логин = {login}', extra={'id_str':id_str, 'id_int':id_int})
        mes_dict['login'] = login
    return mes_dict


def category(mes):
    category_query = 'SELECT category_name FROM category'
    result = execute_sql('select_all', category_query)
    catergory_list = [row[0] for row in result] if result else []

    category_text = ', '.join(catergory_list)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    prompt_name = 'first_category'
    prompt_scheme = mes['prompt']

    logging.info('category', extra={'id_str':id_str, 'id_int':id_int})

    with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    template = next(
        (d['template'] for d in prompt_data if d['name'] == prompt_name), ''
    ).replace('<', '{').replace('>', '}')

    prompt = template.format(category_text=category_text)
    story = all_mes_on_day(mes, sql=False)
    promt_mes = {"role": "system", "content": prompt}
    story.insert(0, promt_mes)

    ans = gpt(story)
    logging.info(f'Отданная категория: {ans}', extra={'id_str':id_str, 'id_int':id_int})

    story_query = """
        UPDATE ChatStory 
        SET category = %s 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    story_params = (ans, id_int, id_str, chatBot)
    execute_sql('update', story_query, story_params)

    if ans in catergory_list:
        query = """
            UPDATE ChatParameters 
            SET category = %s 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        params = (ans, id_int, id_str, chatBot)
        
        logging.info(f'Записанная категория: {ans}', extra={'id_str':id_str, 'id_int':id_int})
    else:
        query = """
            UPDATE ChatParameters 
            SET category = "Категория неопределена" 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        params = (id_int, id_str, chatBot)

        logging.info(f'Отданная категория: Категория неопределена', extra={'id_str':id_str, 'id_int':id_int})

    execute_sql('update', query, params)


def prompt(mes):
    login = mes['login']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    logging.info('prompt', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT cat.scheme, cat.is_prompt
        FROM ChatParameters c

        JOIN category cat ON c.category = cat.category_name
        WHERE c.id_int = %s AND c.id_str = %s AND c.chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    row_category = execute_sql('select_one', query, params)

    if row_category is not None and row_category[1] == 1:
        logging.info('Запускается сбор промпта ', extra={'id_str':id_str, 'id_int':id_int})
        schema = row_category[0]
        prompt_obj = text_prompt.Prompt(login, schema, mes)
        text = prompt_obj.start('start', '')

        if text == 'to_disp':
            logging.info('to_disp', extra={'id_str':id_str, 'id_int':id_int})
            prompt_query = """
                UPDATE ChatParameters 
                SET prompt = %s 
                WHERE id_int = %s AND id_str = %s AND chat_bot = %s
            """
            prompt_params = (text, id_int, id_str, chatBot)
        else:
            logging.info('Собран промпт без параметров. Сбор параметров.', extra={'id_str':id_str, 'id_int':id_int})
            text_with_params = str(extract_words(text, login)).replace('"', '\"').replace("'", '\"')
            prompt_query = """
                UPDATE ChatParameters 
                SET prompt = %s 
                WHERE id_int = %s AND id_str = %s AND chat_bot = %s
            """
            prompt_params = (text_with_params, id_int, id_str, chatBot)

        execute_sql('update', prompt_query, prompt_params)


def all_mes_category(mes):
    query_get_categories = 'SELECT category_name FROM category'
    result = execute_sql('select_all', query_get_categories, None)
    category_list = [row[0] for row in result] if result else []
    category_text = ', '.join(category_list)

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']

    logging.info('all_mes_category', extra={'id_str':id_str, 'id_int':id_int})

    query_get_category = """
        SELECT category 
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params_get_category = (id_int, id_str, chatBot)
    row = execute_sql('select_one', query_get_category, params_get_category)
    category = row[0] if row else "Категория неопределена"

    prompt_name = 'all_mes_category'
    prompt_scheme = mes['prompt']

    try:
        with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
            prompt_data = json.loads(json.loads(res.text))

        template = next(
            (d['template'] for d in prompt_data if d['name'] == prompt_name), ''
        ).replace('<', '{').replace('>', '}')
    except Exception as e:
        logging.debug(f"[Ошибка all_mes_category] {e}")
        logging.error("Произошла ошибка!", exc_info=True)
        template = ''

    story = all_mes_on_day(mes, sql=False, text=True)
    prompt = template.format(category=category, category_text=category_text, story=story)

    gpt_prompt = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": mes['text']}
    ]

    # === Запрос к Mistral с защитой от 429 и None ===
    ans = None
    retry_attempts = 3
    delay = 5  # Начальная задержка

    for attempt in range(retry_attempts):
        try:
            ans = gpt(gpt_prompt)
            if ans is not None:
                break
            else:
                logging.debug('[Предупреждение] LLM вернул None. Повтор...', extra={'id_str':id_str, 'id_int':id_int})
        except Exception as e:
            logging.debug(f'[Ошибка LLM на попытке {attempt + 1}] {e}', extra={'id_str':id_str, 'id_int':id_int})

        if attempt < retry_attempts - 1:
            logging.debug(f'Ждём {delay} секунд перед повтором...', extra={'id_str':id_str, 'id_int':id_int})
            time.sleep(delay)
            delay *= 2  # Экспоненциальный backoff
    else:
        logging.debug(f'[Ошибка] Не удалось получить ответ от Mistral после нескольких попыток.', extra={'id_str':id_str, 'id_int':id_int})
        ans = "Категория неопределена"

    # === Проверяем результат ===
    ans = ans if ans is not None else "Категория неопределена"

    if 'категория' in ans.lower() or ans not in category_list:
        logging.info(f'Ответ: {ans}, категория: {category}', extra={'id_str':id_str, 'id_int':id_int})
        ans = category

    if ans != 'Подключение':# === Обновляем БД ===
        query_update_story = """
            UPDATE ChatStory 
            SET category = %s 
            WHERE id_int = %s AND id_str = %s AND messageId = %s
        """
        params_update_story = (ans, id_int, id_str, messageId)
        execute_sql('update', query_update_story, params_update_story)

        if ans != category:
            final_category = ans if ans in category_list else 'Категория неопределена'
            query_update_parameters = """
                UPDATE ChatParameters 
                SET category = %s 
                WHERE id_int = %s AND id_str = %s AND chat_bot = %s
            """

            logging.info(f'Ответ: {ans}, категория: {final_category}', extra={'id_str':id_str, 'id_int':id_int})
            params_update_parameters = (final_category, id_int, id_str, chatBot)
            execute_sql('update', query_update_parameters, params_update_parameters)


def find_address(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']

    query = """
        SELECT step, category, story 
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params_db = (id_int, id_str, chatBot)
    row = execute_sql('select_one', query, params_db)

    category = row[1] if row and row[1] else ''

    if row and row[0] not in ['houseId_search_mes_sent', 'houseId_search_mes_sent_1']:
        ans = 'Здравствуйте! Пожалуйста, уточните ваш адрес для проверки технической возможности подключения.'
        get_to_1c(
            id_str, id_int, chatBot, messageId, ans, '', category, mes['dt']
        )
        upd_query = """
            UPDATE ChatParameters 
            SET step = "houseId_search_mes_sent" 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        upd_params = (id_int, id_str, chatBot)
        execute_sql('update', upd_query, upd_params)
    elif row and row[0] == 'houseId_search_mes_sent':
        prompt_name = 'support_address_identific'
        prompt_scheme = mes['prompt']

        with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
            prompt_data = json.loads(json.loads(res.text))

        template = next(
            (d['template'] for d in prompt_data if d['name'] == prompt_name), ''
        ).replace('<', '{').replace('>', '}')

        story = all_mes_on_day(mes, sql=False, text=True)
        prompt = template.format(category=category, story=story)
        gpt_prompt = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": mes['text']}
        ]
        ans = gpt(gpt_prompt)
        get_to_1c(
            id_str, id_int, chatBot, messageId, ans, '', category, mes['dt']
        )

        upd_query = """
            UPDATE ChatParameters 
            SET step = "houseId_search_mes_sent_1" 
            WHERE id_int = %s AND id_str = %s AND chat_bot = %s
        """
        upd_params = (id_int, id_str, chatBot)
        execute_sql('update', upd_query, upd_params)
    elif row:
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, '', category, mes['dt'])

    return


def get_houseId(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    query = """
        SELECT address_info
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params_db = (id_int, id_str, chatBot)
    address_str = execute_sql('select_one', query, params_db)[0]
    row = json.loads(address_str)

    mes_dict = mes.copy()

    if row:
        mes_dict['login'] = row['houseid']
    return mes_dict


def prompt_connection_tariffs(mes):

    houseid = mes['login']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    with requests.get(f'{HTTP_REDIS}scheme:prompt') as file:
        text = json.loads(json.loads(file.text))

    query = """
        SELECT scheme
        FROM category 
        WHERE category_name = 'Подключение'
    """
    params_db = ()
    prompt_name = execute_sql('select_one', query, params_db)[0]
    
    connection_prompt = next((name['template'] for name in text if name['name'] == prompt_name), None)

    text_with_params = str(extract_connection_words(connection_prompt, houseid)).replace('"', '\"').replace("'", '\"')
    prompt_query = """
        UPDATE ChatParameters 
        SET prompt = %s 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    prompt_params = (text_with_params, id_int, id_str, chatBot)

    execute_sql('update', prompt_query, prompt_params)


def to_disp(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    login = mes['login']

    ans = 'Передать диспетчеру'
    get_to_1c(id_str, id_int, chatBot, messageId, ans, login, 'Подключение', mes['dt'])


def anser(mes):
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    messageId = mes['messageId']
    login = mes['login']
    date_mes = mes['dt']
    date = date_mes - timedelta(hours=2)

    logging.info(f'anser', extra={'id_str':id_str, 'id_int':id_int})

    query = """
        SELECT cp.prompt, c.is_prompt, c.is_active, cp.category
        FROM ChatParameters cp
        LEFT JOIN category c ON cp.category = c.category_name
        WHERE cp.id_int = %s AND cp.id_str = %s AND cp.dt > %s AND cp.chat_bot = %s
    """
    params = (id_int, id_str, date, chatBot)
    row = execute_sql('select_one', query, params)

    promt = row[0]
    is_prompt = row[1]
    is_active = row[2]
    category = row[3]

    prompt_mes = {"role": "system", "content": promt}
    message = all_mes_on_day(mes, False)
    message.insert(0, prompt_mes)

    if isinstance(promt, str) and 'to_disp' in promt:
        logging.info(f'to_disp', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Передать диспетчеру'
        ins_query = """
            INSERT INTO ChatCategory 
            (id_str, id_int, login, category, prompt, messageId, dt, mes) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        ins_params = (id_str, id_int, login, category, promt, messageId, datetime.now(), ans)
        execute_sql('insert', ins_query, ins_params)
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    elif is_prompt == 1 and is_active == 1 and promt is not None:
        logging.info(f'Активная категория', extra={'id_str':id_str, 'id_int':id_int})
        ans = gpt(message)
        logging.info(f'Ответ: {ans}', extra={'id_str':id_str, 'id_int':id_int})
        if ans is not None:
            if 'испетчер' in ans:
                ans = 'Передать диспетчеру'
            ins_query = """
                INSERT INTO ChatCategory 
                (id_str, id_int, login, category, prompt, messageId, dt, mes) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            ins_params = (
                id_str, id_int, login, category, promt, messageId,
                datetime.now(), ans
            )
            execute_sql('insert', ins_query, ins_params)
        else:
            ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    elif is_prompt == 1 and is_active == 1 and promt is None:
        logging.info(f'Активная категория без промпта, еще одна попытка собрать промпт.', extra={'id_str':id_str, 'id_int':id_int})
        prompt(mes)
        new_prompt_query = """
            SELECT prompt 
            FROM ChatParameters 
            WHERE id_int = %s AND id_str = %s AND dt > %s AND chat_bot = %s
        """
        params_new_prompt = (id_int, id_str, date, chatBot)
        row_new_prompt = execute_sql('select_one', new_prompt_query, params_new_prompt)
        promt_new = row_new_prompt[0]

        if promt_new is None:
            ans = 'Передать диспетчеру'
        else:
            promt_new_mes = {"role": "system", "content": promt_new}
            message[0] = promt_new_mes
            ans = gpt(message)
            if ans is not None:
                if 'испетчер' in ans:
                    ans = 'Передать диспетчеру'
                ans = ans.replace('Ты: ', '')
                ins_query = """
                    INSERT INTO ChatCategory 
                    (id_str, id_int, login, category, prompt, messageId, dt, mes) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                ins_params = (
                    id_str, id_int, login, category, promt, messageId,
                    datetime.now(), ans
                )
                execute_sql('insert', ins_query, ins_params)
            else:
                ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    elif is_prompt == 0 and is_active == 0:
        logging.info(f'Не активная категория', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    elif is_prompt == 0 and is_active == 1:
        logging.info(f'Категория без llm', extra={'id_str':id_str, 'id_int':id_int})
        ans = non_category(mes) if category != 'Благодарность' else 'Рад помочь!'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    elif is_prompt == 1 and is_active == 0:
        logging.info(f'Не активная категория', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])
    else:
        logging.info(f'Не активная категория', extra={'id_str':id_str, 'id_int':id_int})
        ans = 'Передать диспетчеру'
        get_to_1c(id_str, id_int, chatBot, messageId, ans, login, category, mes['dt'])