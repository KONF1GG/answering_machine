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
                logger.debug('gpt: "Да", пытаемся получить адрес', extra={'id_str': id_str, 'id_int': id_int})
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
                logger.debug('gpt: "Нет"', extra={'id_str': id_str, 'id_int': id_int})
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

        logger.debug('Неожиданный ответ от gpt или совпадений не найдено', extra={'id_str': id_str, 'id_int': id_int})
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
    print("=== НАЧАЛО МЕТОДА is_first_mes_on_day ===")
    print(f"Входные данные mes: {mes}")
    
    logger.info('is_first_mes_on_day', extra={'id_str': mes['id_str_sql'], 'id_int': mes['id_int']})
    print("Логирование выполнено")
    
    date = mes['dt']
    dt = date - timedelta(hours=2)
    print(f"Исходная дата: {date}")
    print(f"Дата минус 2 часа: {dt}")

    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    
    print(f"Извлеченные параметры:")
    print(f"  id_int: {id_int}")
    print(f"  id_str: {id_str}")
    print(f"  chatBot: {chatBot}")

    try:
        print("=== ВХОДИМ В TRY БЛОК ===")
        sql = """
            SELECT * FROM ChatParameters 
            WHERE id_int = %s AND id_str = %s AND dt > %s AND chat_bot = %s
        """
        params = (id_int, id_str, dt, chatBot)
        print(f"SQL запрос: {sql}")
        print(f"Параметры запроса: {params}")
        
        row = execute_sql('select_one', sql, params)
        print(f"Результат SQL запроса: {row}")
        print(f"Тип результата: {type(row)}")
        print(f"Результат пустой: {not row}")

        if row:
            print("=== НАЙДЕНЫ ЗАПИСИ - НЕ ПЕРВОЕ СООБЩЕНИЕ ===")
            print(f"Найденная запись: {row}")
            logger.debug('Это не первое сообщение дня', extra={'id_str': id_str, 'id_int': id_int})
            print("=== ВОЗВРАЩАЕМ False ===")
            print("=== КОНЕЦ МЕТОДА is_first_mes_on_day (False) ===")
            return False

        print("=== ЗАПИСИ НЕ НАЙДЕНЫ - ПЕРВОЕ СООБЩЕНИЕ ===")
        logger.info('Это первое сообщение дня', extra={'id_str': id_str, 'id_int': id_int})
        print("=== ВОЗВРАЩАЕМ True ===")
        print("=== КОНЕЦ МЕТОДА is_first_mes_on_day (True) ===")
        return True
        
    except Exception as e:
        print("=== ВХОДИМ В EXCEPT БЛОК ===")
        print(f"Произошла ошибка: {e}")
        print(f"Тип ошибки: {type(e)}")
        logger.error(f'Ошибка в is_first_mes_on_day: {e}', extra={'id_str': id_str, 'id_int': id_int})
        print("=== ВОЗВРАЩАЕМ False (ошибка) ===")
        print("=== КОНЕЦ МЕТОДА is_first_mes_on_day (False) ===")
        return False
    

def is_connection(mes):
    print("=== НАЧАЛО МЕТОДА is_connection ===")
    print(f"Входные данные mes: {mes}")
    
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    
    print(f"Извлеченные параметры:")
    print(f"  id_int: {id_int}")
    print(f"  id_str: {id_str}")
    print(f"  chatBot: {chatBot}")

    sql = """
        SELECT category FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    print(f"SQL запрос: {sql}")
    print(f"Параметры запроса: {params}")
    
    row = execute_sql('select_one', sql, params)
    print(f"Результат SQL запроса: {row}")
    print(f"Тип результата: {type(row)}")
    
    print("Проверяем is_login...")
    is_login_result = is_login(mes)
    print(f"is_login(mes): {is_login_result}")
    print(f"Тип is_login_result: {type(is_login_result)}")
    
    if is_login_result:
        print("=== is_login = True - ВОЗВРАЩАЕМ False ===")
        print("=== КОНЕЦ МЕТОДА is_connection (False) ===")
        return False 
    
    print("is_login = False, продолжаем проверку...")
    
    if row and row[0] == 'Подключение':
        print("=== КАТЕГОРИЯ 'ПОДКЛЮЧЕНИЕ' НАЙДЕНА ===")
        print(f"row[0] (категория): '{row[0]}'")
        print("=== ВОЗВРАЩАЕМ True ===")
        print("=== КОНЕЦ МЕТОДА is_connection (True) ===")
        return True

    print("=== КАТЕГОРИЯ НЕ 'ПОДКЛЮЧЕНИЕ' ИЛИ ROW ПУСТОЙ ===")
    if not row:
        print("row пустой или None")
    else:
        print(f"row[0] (категория): '{row[0]}'")
        print(f"Сравнение с 'Подключение': {row[0] == 'Подключение'}")
    
    print("=== ВОЗВРАЩАЕМ False (по умолчанию) ===")
    print("=== КОНЕЦ МЕТОДА is_connection (False) ===")
    return False


def is_houseId(mes):
    print("=== НАЧАЛО МЕТОДА is_houseId ===")
    print(f"Входные данные mes: {mes}")
    
    id_int = mes['id_int']
    id_str = mes['id_str']
    chatBot = mes['chatBot']
    
    print(f"Извлеченные параметры:")
    print(f"  id_int: {id_int}")
    print(f"  id_str: {id_str}")
    print(f"  chatBot: {chatBot}")

    sql = """
        SELECT address_info
        FROM ChatParameters 
        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
    """
    params = (id_int, id_str, chatBot)
    print(f"SQL запрос: {sql}")
    print(f"Параметры запроса: {params}")
    
    row = execute_sql('select_one', sql, params)
    print(f"Результат SQL запроса: {row}")
    print(f"Тип результата: {type(row)}")

    if row and row[0] not in ['', None]:
        print("=== РЯД СУЩЕСТВУЕТ И НЕ ПУСТОЙ ===")
        print(f"row[0] (address_info): {row[0]}")
        print(f"Тип row[0]: {type(row[0])}")
        
        print("Парсим JSON из address_info...")
        try:
            address_info = json.loads(row[0])
            print(f"Распарсенный address_info: {address_info}")
            print(f"Тип address_info: {type(address_info)}")
            print(f"Ключи в address_info: {list(address_info.keys()) if isinstance(address_info, dict) else 'Не словарь'}")
        except Exception as e:
            print(f"Ошибка при парсинге JSON: {e}")
            print("=== ВОЗВРАЩАЕМ False (ошибка парсинга) ===")
            print("=== КОНЕЦ МЕТОДА is_houseId (False) ===")
            return False

        print("Проверяем наличие 'houseid' в address_info...")
        if 'houseid' in address_info:
            print(f"'houseid' найден в address_info: {address_info['houseid']}")
            print(f"Тип houseid: {type(address_info['houseid'])}")
            
            if address_info['houseid'] is not None:
                print("houseid не None - адрес найден!")
                print("=== ВОЗВРАЩАЕМ True ===")
                print("=== КОНЕЦ МЕТОДА is_houseId (True) ===")
                return True
            else:
                print("houseid равен None")
        else:
            print("'houseid' не найден в address_info")
    else:
        print("=== РЯД НЕ СУЩЕСТВУЕТ ИЛИ ПУСТОЙ ===")
        if not row:
            print("row пустой или None")
        else:
            print(f"row[0] пустой или None: '{row[0]}'")

    print("=== ВОЗВРАЩАЕМ False (по умолчанию) ===")
    print("=== КОНЕЦ МЕТОДА is_houseId (False) ===")
    return False



def is_address_info_mes(mes):
    print("=== НАЧАЛО МЕТОДА is_address_info_mes ===")
    print(f"Входные данные mes: {mes}")
    
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']
    prompt_scheme = mes['prompt']
    prompt_name = 'first_identification'
    
    print(f"Извлеченные параметры:")
    print(f"  id_int: {id_int}")
    print(f"  id_str: {id_str}")
    print(f"  chatBot: {chatBot}")
    print(f"  prompt_scheme: {prompt_scheme}")
    print(f"  prompt_name: {prompt_name}")

    print("Запрашиваем данные промпта из Redis...")
    with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
        print(f"Статус ответа Redis: {res.status_code}")
        print(f"Текст ответа Redis: {res.text}")
        prompt_data = json.loads(json.loads(res.text))
        print(f"Данные промпта получены: {prompt_data}")

    print("Ищем нужный шаблон промпта...")
    prompt = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '')
    print(f"Найденный шаблон: {prompt}")
    
    print("Получаем историю сообщений...")
    story = af.all_mes_on_day(mes, sql=False)
    print(f"История сообщений: {story}")
    
    promt_mes = {"role": "system", "content": prompt}
    print(f"Созданный промпт для системы: {promt_mes}")
    
    story.insert(0, promt_mes)
    print(f"История с добавленным системным промптом: {story}")

    print("Отправляем запрос в gpt...")
    ans = gpt(story)
    print(f"Ответ от gpt: {ans}")
    print(f"Тип ответа: {type(ans)}")

    if type(ans) == str:
        print("Ответ является строкой")
        print(f"Проверяем, содержится ли ответ в ['Да', 'Да.', 'да', 'да.']")
        if ans in ['Да', 'Да.', 'да', 'да.']:
            print("=== ОТВЕТ 'ДА' - ОБРАБАТЫВАЕМ АДРЕС ===")
            print("Ждем 1 секунду...")
            time.sleep(1)
            
            print("Получаем текстовую историю...")
            story_text = af.all_mes_on_day(mes, sql=False, text=True) + mes['text']
            print(f"Текстовая история для запроса адреса: {story_text}")
            
            print("Запрашиваем адрес...")
            with requests.get(f'{HTTP_ADDRESS}adress?query={story_text}') as address_response:
                print(f"Статус ответа адресного сервиса: {address_response.status_code}")
                print(f"Текст ответа адресного сервиса: {address_response.text}")
                data_adsress = json.loads(address_response.text)
                print(f"Данные адреса: {data_adsress}")
                
            if data_adsress:
                print("=== АДРЕС НАЙДЕН - СОХРАНЯЕМ ===")
                login_serv_query = 'update ChatParameters set address_info = %s where id_int = %s and id_str = %s and chat_bot = %s'
                login_serv_params = (str(data_adsress).replace("'", '"').replace('None', 'null'), id_int, id_str, chatBot)
                print(f"SQL запрос на сохранение адреса: {login_serv_query}")
                print(f"Параметры сохранения: {login_serv_params}")
                
                execute_sql('update', login_serv_query, login_serv_params)
                print("Адрес сохранен в базу данных")
                print("=== ВОЗВРАЩАЕМ True ===")
                print("=== КОНЕЦ МЕТОДА is_address_info_mes (True) ===")
                return True
            else:
                print("=== АДРЕС НЕ НАЙДЕН ===")
                print("=== ВОЗВРАЩАЕМ False ===")
                print("=== КОНЕЦ МЕТОДА is_address_info_mes (False) ===")
                return False
        else:
            print(f"Ответ не 'Да', а: '{ans}'")
    else:
        print(f"Ответ не является строкой, тип: {type(ans)}")

    print("=== ВОЗВРАЩАЕМ False (по умолчанию) ===")
    print("=== КОНЕЦ МЕТОДА is_address_info_mes (False) ===")
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