import json

import requests

from config import DADATA_TOKEN, HTTP_REDIS, HTTP_VECTOR
from connections import execute_sql
from services.llm import mistral


def select_login_based_on_service(mes, logins, login_data):
    """Выбирает логин на основе наличия сервиса в данных о логинах."""
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    first_login = logins[0]  # Первый логин из списка
    second_login = logins[1]  # Второй логин из списка
    
    first_service = login_data[first_login]['service']  # Сервис для первого логина
    second_service = login_data[second_login]['service']  # Сервис для второго логина

    # Проверяем, у какого логина есть сервис, и возвращаем его
    if first_service is None and second_service is not None:
        login = second_login.split(':')[1]
        query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
        params = (login, id_int, id_str, chatBot)
        execute_sql('update', query, params)
        return True
    elif second_service is None and first_service is not None:
        login = first_login.split(':')[1]
        query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
        params = (login, id_int, id_str, chatBot)
        execute_sql('update', query, params)
        return True
    else:
        return False

def find_login(mes):
    """Находит логин на основе адреса, извлеченного из сообщения."""
    message = mes['text']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']


    # Промпт для извлечения адреса из сообщения
    with requests.get(f'{HTTP_VECTOR}address?query={message}') as response:
        data = json.loads(response.text)

    example = data[0]['address'] + ', ' + data[1]['address'] + ', ' + data[2]['address']
    prompt_name = 'address_identification'
    prompt_scheme = mes['prompt']

    with requests.get(f'{HTTP_REDIS}{prompt_scheme}') as res:
        prompt_data = json.loads(json.loads(res.text))

    template = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '').replace('<', '{').replace('>', '}')

    address_extraction_prompt = template.format(example=example)

    select_query = 'select story from ChatParameters where id_int = %s and id_str = %s and chat_bot = %s'
    select_params = (id_int, id_str, chatBot)
    row = execute_sql('select_one', select_query, select_params)
    story = row[0]

    message = []
    message = json.loads(story.replace("'", '"').replace('\"', '"')) 
    promt_new_mes = {"role": "system", "content": address_extraction_prompt}
    message.insert(0, promt_new_mes)

    # Извлекаем адрес с помощью API Mistral
    extracted_address = mistral(message)

    # Настройка запроса к API Dadata
    dadata_url = 'http://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address'
    dadata_request_data = {"query": extracted_address}  # Тело запроса
    dadata_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {DADATA_TOKEN}"
    }

    # Отправляем запрос в Dadata
    dadata_response = requests.post(dadata_url, headers=dadata_headers, data=json.dumps(dadata_request_data)).json()

    # Обрабатываем ответ Dadata
    if dadata_response['suggestions']:
        dadata_suggestion = dadata_response['suggestions'][0]  # Берем первый результат
        flat_number = dadata_suggestion['data']['flat']  # Извлекаем номер квартиры

        # Получаем FIAS ID для дальнейших запросов
        fias_id = (
            dadata_suggestion['data']['house_fias_id'] or dadata_suggestion['data']['fias_id']
        ).replace('-', '%20')

        # Запрашиваем данные о доме через кастомный API
        with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:adds.fias%20%27@fiasUUID:%27{fias_id}%27') as house_response:
            house_data = json.loads(house_response.text)

        if house_data:
            house_id = list(house_data.keys())[0].split(':')[1]  # Извлекаем ID дома
        else:
            return False

        # Запрашиваем список логинов, связанных с этим домом
        login_query_url = (
            f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:login%20%27@houseId:[{house_id}%20{house_id}]%27%20Limit%200%20500'
        )

        with requests.get(login_query_url) as login_response:
            login_data = json.loads(login_response.text)

        if type(login_data) is dict:
            logins = list(login_data.keys())

            # Сопоставляем логины с номером квартиры, если он указан
            if flat_number:
                matching_logins = [
                    login for login in logins
                    if login_data[login]['flat'] == int(flat_number)
                ]

                # Логика обработки логинов с учетом их количества
                if len(matching_logins) > 2:
                    return False
                elif len(matching_logins) == 2:
                    return select_login_based_on_service(mes, matching_logins, login_data)
                elif len(matching_logins) == 1:
                    login = matching_logins[0].split(':')[1]
                    login_serv_query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
                    login_serv_params = (login, id_int, id_str, chatBot)
                    execute_sql('update', login_serv_query, login_serv_params)
                    return True
                else:
                    return False

            # Обработка случаев, когда номер квартиры не указан
            elif not flat_number and len(logins) > 2:
                return False
            elif len(logins) == 2:
                return select_login_based_on_service(mes, logins, login_data)
            elif len(logins) == 1:
                login = logins[0].split(':')[1]
                login_flat_query = 'update ChatParameters set login_ai = %s where id_int = %s and id_str = %s and chat_bot = %s'
                login_flat_params = (login, id_int, id_str, chatBot)
                execute_sql('update', login_flat_query, login_flat_params)
                return True
            else:
                return False
        else:
            return False
    else:
        return False