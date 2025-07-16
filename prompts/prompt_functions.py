import logging
from datetime import datetime, timedelta
import json
import requests

from config import HTTP_1C, HTTP_REDIS, HTTP_VECTOR

# Логгер
logger = logging.getLogger(__name__)


def getVector(text, mes):
    logger.info('getVector', extra={'login': mes.get('login', 'unknown')})
    with requests.get(f'{HTTP_VECTOR}promt?query={mes}') as response:
        data = json.loads(response.text)
    a = data[0]['template']
    text += data[0]['template']
    return text


def isAvans(login):
    logger.info('isAvans', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as response:
            data = json.loads(json.loads(response.text))
        service_type = data['service_type']
        if 'Абонплата' in service_type:
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isAvans: {e}', extra={'login': login})
        return False


def isInstallment(login):
    logger.info('isInstallment', extra={'login': login})
    try:
        with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=%D0%A0%D0%B0%D1%81%D1%81%D1%80%D0%BE%D1%87%D0%BA%D0%B8&login={login}') as response:
            installments = json.loads(response.text)

        for installment in installments:
            if 'count' in installment and installment['count'] == 1:
                return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isInstallment: {e}', extra={'login': login})
        return False


def isBlocked(login):
    logger.info('isBlocked', extra={'login': login})
    try:
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
    except Exception as e:
        logger.error(f'Ошибка в isBlocked: {e}', extra={'login': login})
        return False


def isIndexing(login):
    logger.info('isIndexing', extra={'login': login})
    try:
        with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={login}') as response:
            data = json.loads(response.text)

        for element_data in data:
            if 'description' in element_data and element_data['description'] != 'Нет изменений':
                return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isIndexing: {e}', extra={'login': login})
        return False


def isFailure(login):
    logger.info('isFailure', extra={'login': login})
    try:
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
    except Exception as e:
        logger.error(f'Ошибка в isFailure: {e}', extra={'login': login})
        return False


def isGpon(login):
    logger.info('isGpon', extra={'login': login})
    try:
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
    except Exception as e:
        logger.error(f'Ошибка в isGpon: {e}', extra={'login': login})
        return False


def isDiscount(login):
    logger.info('isDiscount', extra={'login': login})
    try:
        with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=discount&login={login}') as response:
            discounts = json.loads(response.text)

        if discounts != []:
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isDiscount: {e}', extra={'login': login})
        return False


def isNotPayment(login):
    logger.info('isNotPayment', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        payment = get_login['payment']
        payment_next = get_login['paymentNext']
        if int(payment) == 0 and not payment_next:
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isNotPayment: {e}', extra={'login': login})
        return False


def IsPauseAndPayment(login):
    logger.info('IsPauseAndPayment', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        next_payment = get_login.get('paymentNext', False)

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
    except Exception as e:
        logger.error(f'Ошибка в IsPauseAndPayment: {e}', extra={'login': login})
        return False


def isVisitScheduled(login):
    logger.info('isVisitScheduled', extra={'login': login})
    try:
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
    except Exception as e:
        logger.error(f'Ошибка в isVisitScheduled: {e}', extra={'login': login})
        return False


def isFutureVisit(login):
    logger.info('isFutureVisit', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}loginplan:{login}') as response:
            data = json.loads(json.loads(response.text))

        start = int(data['start'])

        visit_date = datetime.fromtimestamp(start).date()
        today_date = datetime.now().date()

        if visit_date < today_date:
            return False
        return True
    except Exception as e:
        logger.error(f'Ошибка в isFutureVisit: {e}', extra={'login': login})
        return False


def isServise(login):
    logger.info('isServise', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}loginplan:{login}') as response:
            data = json.loads(json.loads(response.text))

        type_visit = data['typeBP']

        if type_visit == 'Подключение':
            return False
        return True
    except Exception as e:
        logger.error(f'Ошибка в isServise: {e}', extra={'login': login})
        return False


def isCamera(login):
    logger.info('isCamera', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as response:
            data = json.loads(json.loads(response.text))

        services = data['services']

        for service in services:
            if 'Видеонаблюдение' in service['line']:
                return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isCamera: {e}', extra={'login': login})
        return False


def isBlockedCamera(login):
    logger.info('isBlockedCamera', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as response:
            data = json.loads(json.loads(response.text))

        services = data['services']

        for service in services:
            if 'Видеонаблюдение' in service['line']:
                if service['status'] == 'Активный':
                    return False
                return True
        return True
    except Exception as e:
        logger.error(f'Ошибка в isBlockedCamera: {e}', extra={'login': login})
        return True


def isWired(login):
    logger.info('isWired', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')

        houseId = get_login['houseId']

        with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
            get_house = json.loads(json.loads(get_house_text.text))

        if contype == '':
            contype = get_house['conn_type'][0]

        if contype == 'wireles':
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isWired: {e}', extra={'login': login})
        return False


def isWireless(login):
    logger.info('isWireless', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')

        houseId = get_login['houseId']

        with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
            get_house = json.loads(json.loads(get_house_text.text))

        if contype == '':
            contype = get_house['conn_type'][0]

        if contype == 'wireless':
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isWireless: {e}', extra={'login': login})
        return False


def isInternet(login):
    logger.info('isInternet', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        if 'servicecats' in get_login and 'internet' in get_login['servicecats']:
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isInternet: {e}', extra={'login': login})
        return False


def isSibay(login):
    logger.info('isSibay', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        if get_login['territory'] == 'Сибай (SB)':
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isSibay: {e}', extra={'login': login})
        return False


def isIntercom(login):
    logger.info('isIntercom', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        if 'servicecats' in get_login and 'intercom' in get_login['servicecats']:
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isIntercom: {e}', extra={'login': login})
        return False


def isBlockedIntercom(login):
    logger.info('isBlockedIntercom', extra={'login': login})
    try:
        with requests.get(f'{HTTP_REDIS}login:{login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))

        if 'servicecats' in get_login and 'intercom' in get_login['servicecats']:
            time_to = get_login['servicecats']['intercom']['timeto']
        else:
            time_to = get_login['time_to']

        if datetime.fromtimestamp(time_to) < datetime.now():
            return True
        return False
    except Exception as e:
        logger.error(f'Ошибка в isBlockedIntercom: {e}', extra={'login': login})
        return False


def isAbon(login):
    logger.info('isAbon', extra={'login': login})
    try:
        if login == '':
            return False
        return True
    except Exception as e:
        logger.error(f'Ошибка в isAbon: {e}', extra={'login': login})
        return False