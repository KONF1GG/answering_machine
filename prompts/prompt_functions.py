from datetime import datetime, timedelta
import json

import requests

from config import HTTP_1C, HTTP_REDIS, HTTP_VECTOR

#запрос в векторную базу
def getVector(text, mes):
    with requests.get(f'{HTTP_VECTOR}promt?query={mes}') as response:
        data = json.loads(response.text)
    a = data[0]['template']
    text += data[0]['template']
    
    return text

    
# Проверка на наличие абонплаты
def isAvans(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        data = json.loads(json.loads(response.text))
    service_type = data['service_type']
    if 'Абонплата' in service_type:
        return True
    return False

# проверка на наличие рассрочки
def isInstallment(login):
    with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=%D0%A0%D0%B0%D1%81%D1%81%D1%80%D0%BE%D1%87%D0%BA%D0%B8&login={login}') as response:
            installments = json.loads(response.text)
        
    for installment in installments:
        if 'count' in installment:
            if installment['count'] == 1:
                    return True       
    return False

# Проверка на блокировку
def isBlocked(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        data = json.loads(json.loads(response.text))

    if 'servicecats' in data:
        if 'response' in data['servicecats']:
            time_to = data['servicecats']['response']['timeto']
        else:
            time_to = data['time_to']
    else:
        time_to = data['time_to']

    if time_to is None:
        return True 
    
    if datetime.fromtimestamp(time_to) < datetime.now():
        return True
    return False

# Проверка на индексацию
def isIndexing(login):
    with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={login}') as response:
        data = json.loads(response.text)
    
    for element_data in data:
        if 'description' in element_data:
            if element_data['description'] != 'Нет изменений':
                return True
    return False

# Проверка на наличие ошибок
def isFailure(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        data = json.loads(json.loads(response.text))

    if 'hostId' in data:
        hostId = data['hostId']
    else:
        hostId = ''
    addressCodes = data['addressCodes']
        
    if hostId:
        with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@host:[{hostId}%20{hostId}]%27') as fai_host:
            data = fai_host.text
        if data != 'false':
            return True
        
    for address in addressCodes:
        with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@address:[{address}%20{address}]%27') as fai_add:
            data = fai_add.text
        if data != 'false':
            return True       
    return False


def isGpon(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
        get_login = json.loads(json.loads(get_login_text.text))
        
    contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')

    houseId = get_login['houseId']

    with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
        get_house = json.loads(json.loads(get_house_text.text))

    if contype == '':
        contype = get_house['conn_type'][0]
    pon = ['gpon', 'hpon', 'lpon']
    for type in pon:
        if type in contype:
            return True
    return False


def isDiscount(login):
    with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=discount&login={login}') as response:
        discounts = json.loads(response.text)

    if discounts != []:
        return True
    return False


def isNotPayment(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
        get_login = json.loads(json.loads(get_login_text.text))

    payment = get_login['payment']
    payment_next = get_login['paymentNext']
    if int(payment) == 0 and payment_next == False:
        return True
    return False


def IsPauseAndPayment(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
        get_login = json.loads(json.loads(get_login_text.text))

    next_payment = get_login.get('paymentNext', 'Неизвестно')
    today = datetime.now().day

    houseid = get_login.get('houseId', 'Неизвестно')

    with requests.get(f'{HTTP_REDIS}adds:{houseid}') as houseres:
        house = json.loads(json.loads(houseres.text))

    with requests.get(f'{HTTP_REDIS}terrtar:{house["territoryId"]}') as territory:
        ter = json.loads(json.loads(territory.text))
                
    deactivation_date = ter.get('shutdownday', 0)

    if today < deactivation_date and not next_payment:
        return True
    return False


#Проверка на запланированный выезд
def isVisitScheduled(login):
    with requests.get(f'{HTTP_REDIS}loginplan:{login}') as response:
        data = json.loads(response.text)

    if isinstance(data, bool):
        return False

    data_dict = json.loads(data)
    start = int(data_dict['start'])

    visit_date = datetime.fromtimestamp(start).date()
    yesterday_date = (datetime.now() - timedelta(days=1)).date()

    if visit_date < yesterday_date:
        return False

    return True


#Проверка будущий или прошлый выезд
def isFutureVisit(login):
    with requests.get(f'{HTTP_REDIS}loginplan:{login}') as response:
        data = json.loads(json.loads(response.text))

    start = int(data['start'])

    visit_date = datetime.fromtimestamp(start).date()
    today_date = datetime.now().date()

    if visit_date < today_date:
        return False
    
    return True


#Проверка тип выезда
def isServise(login):
    with requests.get(f'{HTTP_REDIS}loginplan:{login}') as response:
        data = json.loads(json.loads(response.text))

    type_visit = data['typeBP']

    if type_visit == 'Подключение':
        return False
    
    return True


def isCamera(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        data = json.loads(json.loads(response.text))

    services = data['services']

    for service in services:
        if 'Видеонаблюдение' in service['line']:
            return True
    return False


def isBlockedCamera(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as response:
        data = json.loads(json.loads(response.text))

    services = data['services']

    for service in services:
        if 'Видеонаблюдение' in service['line']:
            if service['status'] == 'Активный':
                return False
            return True
        
    return True

    
def isWired(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
        get_login = json.loads(json.loads(get_login_text.text))
        
    contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')

    houseId = get_login['houseId']

    with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
        get_house = json.loads(json.loads(get_house_text.text))

    if contype == '':
        contype = get_house['conn_type'][0]
    type = 'wired'
    if type == contype:
        return True
    return False


def isWireless(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
        get_login = json.loads(json.loads(get_login_text.text))
        
    contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')

    houseId = get_login['houseId']

    with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
        get_house = json.loads(json.loads(get_house_text.text))

    if contype == '':
        contype = get_house['conn_type'][0]
    type = 'wireless'
    if type == contype:
        return True
    return False


def isInternet(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))
        
    if 'servicecats' in get_login:
            if 'internet' in get_login['servicecats']:
                return True
    return False

def isSibay(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))
        
    if get_login['territory'] == 'Сибай (SB)':
        return True
    return False


def isIntercom(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))
        
    if 'servicecats' in get_login:
            if 'intercom' in get_login['servicecats']:
                return True
    return False


def isBlockedIntercom(login):
    with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))
        
    if 'servicecats' in get_login:
            if 'intercom' in get_login['servicecats']:
                time_to = get_login['servicecats']['intercom']['timeto']
    else:
        time_to = get_login['time_to']
    
    if datetime.fromtimestamp(time_to) < datetime.now():
        return True
    return False


def isAbon(login):
    if login == '':
        return False
    return True