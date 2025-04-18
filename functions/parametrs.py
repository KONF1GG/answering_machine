import requests
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

REDIS = 'https://ws.freedom1.ru/redis/'

class Abonent:
    def __init__(self, login):
        with requests.get(f'{REDIS}login:{login}') as response:
            self.data = json.loads(json.loads(response.text))
        
        self.login = login

    
    def balance(self):
        return str(self.data.get('balance', 0))
    
    
    def recommended_payment(self):
        next_payment = self.data['paymentNext']
        payment = str(self.data.get('payment', 0))

        if next_payment:
            return f'за следующий период: {payment}'
        else:
            return f'для возобновления услуг: {payment}'


    def contract_number(self):
        return str(self.data.get('contract', 'Неизвестно'))
    
    
    def current_date(self):
        return datetime.now().strftime('%d.%m.%Y')
    
    
    def service_end_date(self):
        try:
            if 'response' in self.data['servicecats']:
                time_to = self.data['servicecats']['response'].get('timeto')
            else:
                time_to = self.data.get('time_to')

            dt = datetime.fromtimestamp(time_to)
            return dt.strftime('%d.%m.%Y %H:%M:%S')
        except:
            return 'Нет информации'
        
  
    def autopay_status(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=last_payment&login={self.login}') as response:
            data = json.loads(response.text)

        try:
            if data['autopay'] == True:
                return 'включен'
        except:
            return 'отключен'


    def deactivation_date(self):
        houseid = self.data.get('houseId', 'Неизвестно')

        try:
            with requests.get(f'{REDIS}adds:{houseid}') as houseres:
                house = json.loads(json.loads(houseres.text))

            with requests.get(f'{REDIS}terrtar:{house["territoryId"]}') as territory:
                ter = json.loads(json.loads(territory.text))
                
            return str(ter.get('shutdownday', 'Неизвестно'))
        except:
            return 'Нет информации'


    def failure_description(self):
        if 'hostId' in self.data:
            hostId = self.data['hostId']
        else:
            hostId = ''
        addressCodes = self.data['addressCodes']
            
        if hostId != '':
            with requests.get(f'{REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@host:[{hostId}%20{hostId}]%27') as fai_host:
                fail_data = fai_host.text
            if fail_data != 'false':
                return 'В данный момент наблюдается авария'
            
        for adress in addressCodes:
            with requests.get(f'{REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@address:[{adress}%20{adress}]%27') as fai_add:
                fai_data = fai_add.text
            if fai_data != 'false':
                return 'В данный момент наблюдается авария'
            
        return 'В данный момент аварии нет'
    

    def failure_mes(self):

        messages = {'BEZ_SROKA': 'В настоящее время фиксируются перебои с доступом к услугам . Мы уже работаем над устранением неисправностей. Приносим извинения за доставленные неудобства.',
                    'Avariya_net_sveta':'В вашем населенном пункте проводятся аварийно-восстановительные работы на электросетях. Приносим извинения за доставленные неудобства и надееемся на Ваше понимание.',
                    'PLANOVOE_NET_SVETA':'В связи с проведением плановых работ электросетевой компанией в Вашем населенном пункте возможны временные отключения услуг связи до конца рабочего дня. Надеемся на Ваше понимание.',
                    'REMONT':'С целью улучшения качества услуг связи на сети проводятся профилактические работы. В течение часа возможны кратковременные ограничения в предоставлении услуг. Приносим извинения за доставленные неудобства и надееемся на Ваше понимание',
                    'POGODA':'По причине неблагоприятных метеоусловий возможны перерывы в оказании услуг связи. Мы прилагаем все усилия для скорейшего восстановления доступа к услугам . Надеемся на Ваше понимание.',
                    'NET_INETA_NET_SROKA':'В настоящее время в Вашем населенном пункте фиксируется Аварийная ситуация . Мы уже работаем над устранением неисправностей . Приносим извинения за доставленные неудобства.'}    

        if 'hostId' in self.data:
            hostId = self.data['hostId']
        else:
            hostId = ''
        addressCodes = self.data['addressCodes']
            
        if hostId != '':
            with requests.get(f'{REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@host:[{hostId}%20{hostId}]%27') as fai_host:
                fail_data = json.loads(fai_host.text)
            if fail_data != 'false':
                key = next(iter(fail_data))
                message = fail_data[key].get('message')
                return messages[message]
            
        for adress in addressCodes:
            with requests.get(f'{REDIS}raw?query=FT.SEARCH%20idx:failure%20%27@address:[{adress}%20{adress}]%27') as fai_add:
                fai_data = fai_add.text
            if fai_data != 'false':
                key = next(iter(fail_data))
                message = fail_data[key].get('message')
                return messages[message]
            
        return 'В данный момент аварии нет'


    def transactions(self):
        mount_pred = datetime.now() + relativedelta(months=-1)
        mount_last = datetime.now() + relativedelta(months=+1)
        uuid = self.data.get('UUID', 'Неизвестно')
        try:
            with requests.get(
                f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Cabinet/getBalanceHistory?UUID={uuid}&start={mount_pred.strftime("%Y-%m")}-01T00:00:00&end={mount_last.strftime("%Y-%m")}-01T00:00:00'
            ) as pay_mounth:
                pays = json.loads(pay_mounth.text)
            transactions = ''
            for pay in pays:
                if pay.get('Type') != 'Start':
                    transactions += f' Дата: {pay["Date"]}, Пополнение: {pay["Plus"]}, Списание: {pay["Minus"]}, Баланс: {pay["Balance"]}, Тип: {pay["Type"]}, Комментарий: {pay["Comment"]}; '
            return transactions
        except:
            return 'Нет информации'


    def description(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
            data = json.loads(response.text)
            try:
                return data[0]['description']
            except:
                return 'Нет информации'

    
    def sum_indexing(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
            data = json.loads(response.text)
            try:
                return data[0]['sum']
            except:
                return 'Нет информации'


    def tariff_price(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=price_indexation&login={self.login}') as response:
            data = json.loads(response.text)
            try:
                return data[0]['price']
            except:
                return 'Нет информации'


    def payment_mounth(self):
        url = "http://server1c.freedom1.ru/UNF_CRM_WS/hs/Cabinet/allServices"
        msg = self.data.get('UUID', 'Неизвестно')
        try:
            data = {"UUID": msg}
            response = requests.post(url, data=json.dumps(data)).json()
           
            services = response[0]['services']            
            payment_mounth = 0

            for serv in services:
                payment_mounth += int(serv['price'])
            
            return str(payment_mounth)

        except:
            return 'Нет информации'
        
    
    def services_and_statuses(self):
        url = "http://server1c.freedom1.ru/UNF_CRM_WS/hs/Cabinet/getAllServices"
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
        
        except:
            return 'Нет информации'
        
    
    def current_month_amount(self):
        url = "http://server1c.freedom1.ru/UNF_CRM_WS/hs/Cabinet/allServices"
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

        except:
            return 'Нет информации'
        
    
    def mandatory_payments(self):
        url = "http://server1c.freedom1.ru/UNF_CRM_WS/hs/Cabinet/allServices"
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

        except:
            return 'Нет информации'


    def installment_service(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=%D0%A0%D0%B0%D1%81%D1%81%D1%80%D0%BE%D1%87%D0%BA%D0%B8&login={self.login}') as response:
            installments = json.loads(response.text)

        installment_text = ''
        for installment in installments:
            if 'count' in installment:
                if installment['count'] == 1:
                    installment_text += ' Рассрочка ' + str(installment['service']) + ' заканчивается ' + str(installment['enddate']) + ' осталось заплатить ' + str(installment['sum']) + ';' + ' '
        
        return installment_text


    def available_services(self):
        with requests.get(f'{REDIS}login:{self.login}') as get_login_text:
            get_login = json.loads(json.loads(get_login_text.text))
        
        contype = ''
        if 'servicecats' in get_login:
            if 'contype' in get_login['servicecats']['internet']:
                contype = get_login['servicecats']['internet']['contype']

        houseId = get_login['houseId']

        with requests.get(f'{REDIS}adds:{houseId}') as get_house_text:
            get_house = json.loads(json.loads(get_house_text.text))

        territoryId = get_house['territoryId']

        if contype == '':
            contype = get_house['conn_type'][0]
                
        with requests.get(f'{REDIS}terrtar:{territoryId}') as get_ter_text:
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


    def discount(self):
        with requests.get(f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=discount&login={self.login}') as response:
            discounts = json.loads(response.text)

        if discounts[0]:
            discount = str(discounts[0]['discount'])
            if discounts[0]['inPercent']:
                inPercent = '%'
            else:
                inPercent = 'рублей'

            if 'toDate' in discounts[0]:
                toDate_dict = discounts[0]['toDate']
                toDate = f'до {str(toDate_dict)}'
            else:
                toDate = ''

            return f'скидка {discount} {inPercent} {toDate}'
        
    
    def last_pay(self):
        url = f'http://server1c.freedom1.ru/UNF_CRM_WS/hs/Grafana/anydata?query=last_payment&login={self.login}'
        with requests.get(url) as response:
                da = json.loads(response.text)
        try:
            dt = da['date']
            suma = da['sum']

            text = f'{dt} в размере {suma} рублей'
            return text
        except:
            return 'нет информации'

        