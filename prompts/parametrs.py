import logging
from datetime import datetime
import json
import requests
from dateutil.relativedelta import relativedelta
from config import HTTP_1C, HTTP_REDIS

# Логгер
logger = logging.getLogger(__name__)


class Abonent:
    def __init__(self, login):
        logger.info('__init__', extra={'login': login})
        if login != '':
            try:
                with requests.get(f'{HTTP_REDIS}login:{login}') as response:
                    self.data = json.loads(json.loads(response.text))
            except Exception as e:
                logger.error(f'Ошибка при загрузке данных абонента: {e}', extra={'login': login})
                self.data = {}
        else:
            self.data = {}
        self.login = login

    def balance(self):
        logger.info('balance', extra={'login': self.login})
        return str(self.data.get('balance', 0))

    def recommended_payment(self):
        logger.info('recommended_payment', extra={'login': self.login})
        next_payment = self.data['paymentNext']
        payment = str(self.data.get('payment', 0))
        if next_payment:
            return f'за следующий период: {payment}'
        else:
            return f'для возобновления услуг: {payment}'

    def contract_number(self):
        logger.info('contract_number', extra={'login': self.login})
        return str(self.data.get('contract', 'Неизвестно'))

    def current_date(self):
        logger.info('current_date', extra={'login': self.login})
        return datetime.now().strftime('%d.%m.%Y')

    def service_end_date(self):
        logger.info('service_end_date', extra={'login': self.login})
        try:
            if 'response' in self.data['servicecats']:
                time_to = self.data['servicecats']['response'].get('timeto')
            else:
                time_to = self.data.get('time_to')
            dt = datetime.fromtimestamp(time_to)
            return dt.strftime('%d.%m.%Y %H:%M:%S')
        except Exception as e:
            logger.debug('Нет информации о дате окончания услуги', extra={'login': self.login})
            return 'Нет информации'

    def autopay_status(self):
        logger.info('autopay_status', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=last_payment&login={self.login}') as response:
                data = json.loads(response.text)
            if data['autopay'] == True:
                return 'включен'
        except Exception as e:
            logger.debug('Ошибка при получении статуса автоплатежа', extra={'login': self.login})
        return 'отключен'

    def deactivation_date(self):
        logger.info('deactivation_date', extra={'login': self.login})
        houseid = self.data.get('houseId', 'Неизвестно')
        try:
            with requests.get(f'{HTTP_REDIS}adds:{houseid}') as houseres:
                house = json.loads(json.loads(houseres.text))
            with requests.get(f'{HTTP_REDIS}terrtar:{house["territoryId"]}') as territory:
                ter = json.loads(json.loads(territory.text))
            return str(ter.get('shutdownday', 'Неизвестно'))
        except Exception as e:
            logger.debug('Нет информации о дате деактивации', extra={'login': self.login})
            return 'Нет информации'

    def failure_description(self):
        logger.info('failure_description', extra={'login': self.login})
        if 'hostId' in self.data:
            hostId = self.data['hostId']
        else:
            hostId = ''
        addressCodes = self.data['addressCodes']
        if hostId != '':
            try:
                with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@host:[{hostId}%20{hostId}]%27') as fai_host:
                    fail_data = fai_host.text
                if fail_data != 'false':
                    return 'В данный момент наблюдается авария'
            except Exception as e:
                logger.warning('Ошибка при проверке аварии по hostId', extra={'login': self.login})

        for adress in addressCodes:
            try:
                with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@address:[{adress}%20{adress}]%27') as fai_add:
                    fai_data = fai_add.text
                if fai_data != 'false':
                    return 'В данный момент наблюдается авария'
            except Exception as e:
                logger.warning('Ошибка при проверке аварии по адресу', extra={'login': self.login})

        return 'В данный момент аварии нет'

    def failure_mes(self):
        logger.info('failure_mes', extra={'login': self.login})
        messages = {
            'BEZ_SROKA': 'В настоящее время фиксируются перебои с доступом к услугам . Мы уже работаем над устранением неисправностей. Приносим извинения за доставленные неудобства.',
            'Avariya_net_sveta': 'В вашем населенном пункте проводятся аварийно-восстановительные работы на электросетях. Приносим извинения за доставленные неудобства и надееемся на Ваше понимание.',
            'PLANOVOE_NET_SVETA': 'В связи с проведением плановых работ электросетевой компанией в Вашем населенном пункте возможны временные отключения услуг связи до конца рабочего дня. Надеемся на Ваше понимание.',
            'REMONT': 'С целью улучшения качества услуг связи на сети проводятся профилактические работы. В течение часа возможны кратковременные ограничения в предоставлении услуг. Приносим извинения за доставленные неудобства и надееемся на Ваше понимание',
            'POGODA': 'По причине неблагоприятных метеоусловий возможны перерывы в оказании услуг связи. Мы прилагаем все усилия для скорейшего восстановления доступа к услугам . Надеемся на Ваше понимание.',
            'NET_INETA_NET_SROKA': 'В настоящее время в Вашем населенном пункте фиксируется Аварийная ситуация . Мы уже работаем над устранением неисправностей . Приносим извинения за доставленные неудобства.'
        }
        if 'hostId' in self.data:
            hostId = self.data['hostId']
        else:
            hostId = ''
        addressCodes = self.data['addressCodes']
        if hostId != '':
            try:
                with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@host:[{hostId}%20{hostId}]%27') as fai_host:
                    fail_data = json.loads(fai_host.text)
                if fail_data != 'false':
                    key = next(iter(fail_data))
                    message = fail_data[key].get('message')
                    return messages[message]
            except Exception as e:
                logger.warning('Ошибка при получении текста аварии по hostId', extra={'login': self.login})

        for adress in addressCodes:
            try:
                with requests.get(f'{HTTP_REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@address:[{adress}%20{adress}]%27') as fai_add:
                    fai_data = fai_add.text
                if fai_data != 'false':
                    key = next(iter(fail_data))
                    message = fail_data[key].get('message')
                    return messages[message]
            except Exception as e:
                logger.warning('Ошибка при получении текста аварии по адресу', extra={'login': self.login})

        return 'В данный момент аварии нет'

    def transactions(self):
        logger.info('transactions', extra={'login': self.login})
        mount_pred = datetime.now() + relativedelta(months=-1)
        mount_last = datetime.now() + relativedelta(months=+1)
        uuid = self.data.get('UUID', 'Неизвестно')
        try:
            with requests.get(
                f'{HTTP_1C}hs/Cabinet/getBalanceHistory?UUID={uuid}&start={mount_pred.strftime("%Y-%m")}-01T00:00:00&end={mount_last.strftime("%Y-%m")}-01T00:00:00'
            ) as pay_mounth:
                pays = json.loads(pay_mounth.text)
            transactions = ''
            for pay in pays:
                if pay.get('Type') != 'Start':
                    transactions += f' Дата: {pay["Date"]}, Пополнение: {pay["Plus"]}, Списание: {pay["Minus"]}, Баланс: {pay["Balance"]}, Тип: {pay["Type"]}, Комментарий: {pay["Comment"]}; '
            return transactions
        except Exception as e:
            logger.debug('Нет информации о транзакциях', extra={'login': self.login})
            return 'Нет информации'

    def description(self):
        logger.info('description', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
                data = json.loads(response.text)
            return data[0]['description']
        except Exception as e:
            logger.debug('Нет информации о цене', extra={'login': self.login})
            return 'Нет информации'

    def sum_indexing(self):
        logger.info('sum_indexing', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
                data = json.loads(response.text)
            return data[0]['sum']
        except Exception as e:
            logger.debug('Нет информации о сумме индексации', extra={'login': self.login})
            return 'Нет информации'

    def tariff_price(self):
        logger.info('tariff_price', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
                data = json.loads(response.text)
            return data[0]['price']
        except Exception as e:
            logger.debug('Нет информации о цене тарифа', extra={'login': self.login})
            return 'Нет информации'

    def payment_mounth(self):
        logger.info('payment_mounth', extra={'login': self.login})
        url = f"{HTTP_1C}hs/Cabinet/allServices"
        msg = self.data.get('UUID', 'Неизвестно')
        try:
            data = {"UUID": msg}
            response = requests.post(url, data=json.dumps(data)).json()
            services = response[0]['services']
            payment_mounth = 0
            for serv in services:
                payment_mounth += int(serv['price'])
            return str(payment_mounth)
        except Exception as e:
            logger.debug('Нет информации о ежемесячной оплате', extra={'login': self.login})
            return 'Нет информации'

    def services_and_statuses(self):
        logger.info('services_and_statuses', extra={'login': self.login})
        url = f"{HTTP_1C}hs/Cabinet/getAllServices"
        msg = self.data.get('UUID', 'Неизвестно')
        try:
            data = {"UUID": msg}
            response = requests.post(url, data=json.dumps(data)).json()
            services = response[0]['Charges']
            services_and_statuses = ''
            for serv in services:
                if serv['Status'] in ['Активный', 'Приостановлен (без отключения)'] and serv['Charge'] != 'Аренда абонентского оборудования':
                    services_and_statuses += str(serv['Charge']) + ', статус: ' + serv['Status'] + ', стоимость: ' + str(serv['Price']) + ' рублей; '
            return services_and_statuses
        except Exception as e:
            logger.debug('Нет информации о статусах услуг', extra={'login': self.login})
            return 'Нет информации'

    def current_month_amount(self):
        logger.info('current_month_amount', extra={'login': self.login})
        url = f"{HTTP_1C}hs/Cabinet/allServices"
        msg = self.data.get('UUID', 'Неизвестно')
        try:
            data = {"UUID": msg}
            response = requests.post(url, data=json.dumps(data)).json()
            services = response[0]['services']
            current_month_amount = 0
            for serv in services:
                if serv['status'] in ['Активный', 'Приостановлен (без отключения)']:
                    current_month_amount += int(serv['summa'])
            return str(current_month_amount)
        except Exception as e:
            logger.debug('Нет информации о сумме за месяц', extra={'login': self.login})
            return 'Нет информации'

    def mandatory_payments(self):
        logger.info('mandatory_payments', extra={'login': self.login})
        url = f"{HTTP_1C}hs/Cabinet/allServices"
        msg = self.data.get('UUID', 'Неизвестно')
        try:
            data = {"UUID": msg}
            response = requests.post(url, data=json.dumps(data)).json()
            services = response[0]['services']
            mandatory_payments = 0
            for serv in services:
                if 'ренд' in serv['productName'] or 'ассрочк' in serv['productName']:
                    mandatory_payments += int(serv['price'])
            return str(mandatory_payments)
        except Exception as e:
            logger.debug('Нет информации о обязательных платежах', extra={'login': self.login})
            return 'Нет информации'

    def installment_service(self):
        logger.info('installment_service', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=%D0%A0%D0%B0%D1%81%D1%81%D1%80%D0%BE%D1%87%D0%BA%D0%B8&login={self.login}') as response:
                installments = json.loads(response.text)
            installment_text = ''
            for installment in installments:
                if 'count' in installment:
                    if installment['count'] == 1:
                        installment_text += ' Рассрочка ' + str(installment['service']) + ' заканчивается ' + str(installment['enddate']) + ' осталось заплатить ' + str(installment['sum']) + ';' + ' '
            return installment_text
        except Exception as e:
            logger.debug('Нет информации о рассрочках', extra={'login': self.login})
            return 'Нет информации'

    def available_services(self):
        logger.info('available_services', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as get_login_text:
                get_login = json.loads(json.loads(get_login_text.text))
            contype = get_login.get('servicecats', {}).get('internet', {}).get('contype', '')
            houseId = get_login['houseId']
            with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
                get_house = json.loads(json.loads(get_house_text.text))
            territoryId = get_house['territoryId']
            if contype == '':
                contype = get_house['conn_type'][0]
            with requests.get(f'{HTTP_REDIS}terrtar:{territoryId}') as get_ter_text:
                get_ter = json.loads(json.loads(get_ter_text.text))
            tarif_text = ''
            if contype in get_ter:
                tariffs = get_ter[contype]['tariffs']
            elif contype == 'gpon' and 'lpon' in get_ter:
                tariffs = get_ter['lpon']['tariffs']
            elif contype == 'lpon' and 'gpon' in get_ter:
                tariffs = get_ter['gpon']['tariffs']
            else:
                return 'Переключение тарифов невозможно'
            for tarif in tariffs:
                if tarif['available']:
                    del tarif['speedday4site']
                    del tarif['speednight4site']
                    tarif_text += str(tarif) + ', '
            return tarif_text
        except Exception as e:
            logger.debug('Ошибка получения доступных тарифов', extra={'login': self.login})
            return 'Нет информации'

    def discount(self):
        logger.info('discount', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=discount&login={self.login}') as response:
                discounts = json.loads(response.text)
            if discounts[0]:
                discount = str(discounts[0]['discount'])
                inPercent = '%' if discounts[0]['inPercent'] else 'рублей'
                toDate = f"до {discounts[0]['toDate']}" if 'toDate' in discounts[0] else ''
                return f'скидка {discount} {inPercent} {toDate}'
            return 'Нет информации'
        except Exception as e:
            logger.debug('Ошибка при получении информации о скидке', extra={'login': self.login})
            return 'Нет информации'

    def last_pay(self):
        logger.info('last_pay', extra={'login': self.login})
        url = f'{HTTP_1C}hs/Grafana/anydata?query=last_payment&login={self.login}'
        try:
            with requests.get(url) as response:
                da = json.loads(response.text)
            dt = da['date']
            suma = da['sum']
            return f'{dt} в размере {suma} рублей'
        except Exception as e:
            logger.debug('Нет информации о последнем платеже', extra={'login': self.login})
            return 'нет информации'

    def servise_date(self):
        logger.info('servise_date', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}loginplan:{self.login}') as response:
                data = json.loads(json.loads(response.text))
            start = int(data['start'])
            return datetime.fromtimestamp(start).date()
        except Exception as e:
            logger.debug('Ошибка при получении даты подключения', extra={'login': self.login})
            return 'Нет информации'

    def camera_status(self):
        logger.info('camera_status', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as response:
                data = json.loads(json.loads(response.text))
            services = data['services']
            for service in services:
                if 'Видеонаблюдение' in service['line']:
                    name = service['serviceName']
                    status = service['status']
                    count = service['count']
                    return f'Услуга {name}, статус: {status}, количество камер: {count}.'
            return 'Услуга видеонаблюдения не подключена'
        except Exception as e:
            logger.debug('Ошибка при получении статуса камер', extra={'login': self.login})
            return 'Ошибка'

    def contype(self):
        logger.info('contype', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as get_login_text:
                get_login = json.loads(json.loads(get_login_text.text))
            contype = ''
            if 'servicecats' in get_login:
                if 'contype' in get_login['servicecats']['internet']:
                    contype = get_login['servicecats']['internet']['contype']
            houseId = get_login['houseId']
            with requests.get(f'{HTTP_REDIS}adds:{houseId}') as get_house_text:
                get_house = json.loads(json.loads(get_house_text.text))
            if contype == '':
                contype = get_house['conn_type'][0]
            pon = ['gpon', 'hpon', 'lpon']
            for type in pon:
                if type in contype:
                    return 'Оптическая технология подключения.'
            if contype == 'wireles':
                return 'Проводная технология подключения.'
            return 'Беспроводная технология подключения.'
        except Exception as e:
            logger.debug('Ошибка при определении типа подключения', extra={'login': self.login})
            return 'Ошибка'

    def intercom_status(self):
        logger.info('intercom_status', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as response:
                data = json.loads(json.loads(response.text))
            services = data['services']
            for service in services:
                if 'омофон' in service['line']:
                    name = service['serviceName']
                    status = service['status']
                    return f'Услуга {name}, статус: {status}.'
            return 'Услуга домофонии не подключена'
        except Exception as e:
            logger.debug('Ошибка при получении статуса домофона', extra={'login': self.login})
            return 'Ошибка'

    def terrytory_name(self):
        logger.info('terrytory_name', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as response:
                data = json.loads(json.loads(response.text))
            territory = data['territory']
            region = data['region']
            return f'{region}, территория: {territory}'
        except Exception as e:
            logger.debug('Ошибка при получении региона или территории', extra={'login': self.login})
            return 'Ошибка'

    def tv_status(self):
        logger.info('tv_status', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_REDIS}login:{self.login}') as response:
                data = json.loads(json.loads(response.text))
            services = data['services']
            for service in services:
                if '[FR] Фридом.Интерактивное IPTV"' in service['line']:
                    name = service['serviceName']
                    status = service['status']
                    return f'Услуга {name}, статус: {status}.'
            return 'Услуга телевидения не подключена'
        except Exception as e:
            logger.debug('Ошибка при получении статуса ТВ', extra={'login': self.login})
            return 'Ошибка'

    def tariff_info(self):
        logger.info('tariff_info', extra={'login': self.login})
        try:
            ter_id = self.data['territoryId']
            speed = self.data['servicecats']['internet']['speed']
            return f'Тариф: ID территории - {ter_id}, скорость - {speed}'
        except Exception as e:
            logger.debug('Ошибка при получении информации о тарифе', extra={'login': self.login})
            return 'Ошибка'

    def installment_plan(self):
        logger.info('installment_plan', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=%D0%A0%D0%B0%D1%81%D1%81%D1%80%D0%BE%D1%87%D0%BA%D0%B8&login={self.login}') as resp:
                data = json.loads(resp.text)
            text = ''
            total_monthly_payment = 0
            total_full_sum = 0
            if data:
                for item in data:
                    service = item['service']
                    count = item['count']
                    enddate = item['enddate']
                    price = item['price']
                    full_sum = item['sum']
                    total_monthly_payment += price * count
                    total_full_sum += full_sum
                    text += f"{service}, количество устройств: {count}, до {enddate}, ежемесячный платеж: {price}; "
                text += (
                    f"\nОбщий ежемесячный платеж: {total_monthly_payment}. "
                    f"Общая сумма для полного погашения рассрочки: {total_full_sum}."
                )
            else:
                text = 'У абонента нет активной рассрочки.'
            return text
        except Exception as e:
            logger.debug('Ошибка при получении информации о рассрочке', extra={'login': self.login})
            return 'Ошибка'

    def camera_info(self):
        logger.info('camera_info', extra={'login': self.login})
        try:
            services = self.data['services']
            text = ''
            for service in services:
                if 'видеонаблюдение' in service['line'].lower():
                    serviceName = service['serviceName']
                    status = service['status']
                    text += f'{serviceName} статус {status}. '
            return text
        except Exception as e:
            logger.debug('Ошибка при получении информации о камерах', extra={'login': self.login})
            return 'Ошибка'
        
    
    def price(self):
        logger.info('price', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
                data = json.loads(response.text)
            return str(data[0]['price'])
        except Exception as e:
            logger.debug('Нет информации о цене', extra={'login': self.login})
            return 'Нет информации'


    def price_indexing(self):
        logger.info('price_indexing', extra={'login': self.login})
        try:
            with requests.get(f'{HTTP_1C}hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
                data = json.loads(response.text)

                if data[0]['description'] == 'Подорожает':
                    new_price = int(data[0]['price']) + int(data[0]['sum'])
                    return 'Сумма за следующий месяц:' + str(new_price)
                return ''
        except Exception as e:
            logger.debug('Нет информации о цене', extra={'login': self.login})
            return 'Нет информации'