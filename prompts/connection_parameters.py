import requests
import json

from config import HTTP_REDIS


def connection_tariffs(house_id, contype=''):
    with requests.get(f'{HTTP_REDIS}adds:{house_id}') as response:
        house_data = json.loads(json.loads(response.text))

    territory_id = house_data['territoryId']

    if not contype:
        contype = house_data['conn_type'][0]

    with requests.get(f'{HTTP_REDIS}terrtar:{territory_id}') as response:
        territory_data = json.loads(json.loads(response.text))

    tariff_key = contype
    if contype not in territory_data:
        if contype == 'gpon' and 'lpon' in territory_data:
            tariff_key = 'lpon'
        elif contype == 'lpon' and 'gpon' in territory_data:
            tariff_key = 'gpon'
        else:
            return 'Переключение тарифов невозможно'

    tariffs = territory_data[tariff_key]['tariffs']
    tariff_text = ''

    for tariff in tariffs:
        if tariff['available']:
            tariff.pop('speedday4site', None)
            tariff.pop('speednight4site', None)
            tariff_text += str(tariff) + ', '

    return tariff_text


def connection_actions(house_id, contype=''):
    with requests.get(f'{HTTP_REDIS}adds:{house_id}') as response:
        house_data = json.loads(json.loads(response.text))

    territory_id = house_data['territoryId']

    if not contype:
        contype = house_data['conn_type'][0]

    with requests.get(f'{HTTP_REDIS}terrtar:{territory_id}') as response:
        territory_data = json.loads(json.loads(response.text))

    action_key = contype
    if contype not in territory_data:
        if contype == 'gpon' and 'lpon' in territory_data:
            action_key = 'lpon'
        elif contype == 'lpon' and 'gpon' in territory_data:
            action_key = 'gpon'
        else:
            return ''

    actions = territory_data[action_key]['сonnectionPrice']['actions']
    return ' '.join(actions)


def connection_price(house_id, contype=''):
    with requests.get(f'{HTTP_REDIS}adds:{house_id}') as response:
        house_data = json.loads(json.loads(response.text))

    territory_id = house_data['territoryId']

    if not contype:
        contype = house_data['conn_type'][0]

    with requests.get(f'{HTTP_REDIS}terrtar:{territory_id}') as response:
        territory_data = json.loads(json.loads(response.text))

    price = territory_data[contype]['сonnectionPrice']['price']
    return str(price)