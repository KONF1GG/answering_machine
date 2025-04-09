import json
import requests
from config import API_KEY, DADATA_TOKEN
from connections import db_connextion

def mistral(text, prompt):
    import threading
    import time
    from mistralai import Mistral

    timeout = 60

    """Вызывает API Mistral с таймаутом."""
    client = Mistral(api_key=API_KEY)
    model_name = "mistral-large-latest"

    full_prompt = str(prompt) + str(text)

    result = [None]  # Используем список, чтобы изменить его внутри потока

    def call_api():
        try:
            response = client.chat.complete(
                model=model_name,
                messages=[{"role": "user", "content": full_prompt}]
            )
            result[0] = response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка API: {e}")

    thread = threading.Thread(target=call_api)
    thread.start()
    thread.join(timeout)  # Ждем `timeout` секунд

    if thread.is_alive():
        return None

    time.sleep(1)
    return str(result[0]) if result[0] else None


def mistral_large(text, prompt):
    import threading
    import time
    from mistralai import Mistral

    timeout = 60

    """Вызывает API Mistral с таймаутом."""
    client = Mistral(api_key=API_KEY)
    model_name = "mistral-large-latest"

    full_prompt = str(prompt) + str(text)

    result = [None]  # Используем список, чтобы изменить его внутри потока

    def call_api():
        try:
            response = client.chat.complete(
                model=model_name,
                messages=[{"role": "user", "content": full_prompt}]
            )
            result[0] = response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка API: {e}")

    thread = threading.Thread(target=call_api)
    thread.start()
    thread.join(timeout)  # Ждем `timeout` секунд

    if thread.is_alive():
        print("Превышено время ожидания API, прерываем запрос")
        return None

    time.sleep(1)
    return str(result[0]) if result[0] else None

def select_login_based_on_service(mes, logins, login_data):
    """Выбирает логин на основе наличия сервиса в данных о логинах."""
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    first_login = logins[0]
    second_login = logins[1] 
    
    first_service = login_data[first_login]['service']
    second_service = login_data[second_login]['service']

    if first_service is None and second_service is not None:
        login = second_login.split(':')[1]
        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'uptate ChatParameters set login_ai = "{login}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close()
        return True
    elif second_service is None and first_service is not None:
        login = first_login.split(':')[1]
        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'uptate ChatParameters set login_ai = "{login}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
        db_connection.commit()
        db_connection.close
        return True
    else:
        return False

def find_login(mes):
    """Находит логин на основе адреса, извлеченного из сообщения."""
    message = mes['text']
    id_int = mes['id_int']
    id_str = mes['id_str_sql']
    chatBot = mes['chatBot']

    with requests.get(f'http://192.168.111.151:8080/v1/address?query={message}') as response:
        data = json.loads(response.text)

    d0 = data[0] 
    example = data[0]['address'] + ', ' + data[1]['address'] + ', ' + data[2]['address']

    prompt_name = '"address_identification"'

    with requests.get('https://ws.freedom1.ru/redis/scheme:prompt') as res:
        prompt_data = json.loads(json.loads(res.text))

    template = next((d['template'] for d in prompt_data if d['name'] == prompt_name), '').replace('<', '{').replace('>', '}')

    address_extraction_prompt = template.format(example=example, message=message)

    extracted_address = mistral_large('', address_extraction_prompt)

    dadata_url = 'http://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address'
    dadata_request_data = {"query": extracted_address}  # Тело запроса
    dadata_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {DADATA_TOKEN}"
    }

    dadata_response = requests.post(dadata_url, headers=dadata_headers, data=json.dumps(dadata_request_data)).json()

    if dadata_response['suggestions']:
        dadata_suggestion = dadata_response['suggestions'][0]
        flat_number = dadata_suggestion['data']['flat']

        fias_id = (
            dadata_suggestion['data']['house_fias_id'] or dadata_suggestion['data']['fias_id']
        ).replace('-', '%20')

        with requests.get(f'https://ws.freedom1.ru/redis/raw?query=FT.SEARCH%20idx:adds.fias%20%27@fiasUUID:%27{fias_id}%27') as house_response:
            house_data = json.loads(house_response.text)



        if house_data:
            house_id = list(house_data.keys())[0].split(':')[1]
        else:
            return False
        login_query_url = (
            f'https://ws.freedom1.ru/redis/raw?query=FT.SEARCH%20idx:login%20%27@houseId:[{house_id}%20{house_id}]%27%20Limit%200%20500'
        )

        with requests.get(login_query_url) as login_response:
            login_data = json.loads(login_response.text)

        if type(login_data) is dict:
            logins = list(login_data.keys())

            if flat_number:
                matching_logins = [
                    login for login in logins
                    if login_data[login]['flat'] == int(flat_number)
                ]

                if len(matching_logins) > 2:
                    return False
                elif len(matching_logins) == 2:
                    return select_login_based_on_service(mes, matching_logins, login_data)
                elif len(matching_logins) == 1:
                    login = matching_logins[0].split(':')[1]
                    db_connection = db_connextion()
                    cur = db_connection.cursor(buffered=True)
                    cur.execute(f'update ChatParameters set login_ai = "{login}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
                    db_connection.commit()
                    db_connection.close()
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
                db_connection = db_connextion()
                cur = db_connection.cursor(buffered=True)
                cur.execute(f'update ChatParameters set login_ai = "{login}" where id_int = {id_int} and id_str = "{id_str}" and chat_bot = "{chatBot}"')
                db_connection.commit()
                db_connection.close()
                return True
            else:
                return False
        else:
            return False
    else:
        return False