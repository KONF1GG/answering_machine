import json

import requests

from config import HTTP_VECTOR

def getVector_one(text, mes):
    with requests.get(f'{HTTP_VECTOR}promt?query={mes}') as response:
        data = json.loads(response.text)

    text += data[0]['template']
    
    return text


def getVector_two(text, mes):
    with requests.get(f'{HTTP_VECTOR}promt?query={mes}') as response:
        data = json.loads(response.text)

    text += data[0]['template'] + '\n' + data[1]['template']
    
    return text


def getVector_three(text, mes):
    with requests.get(f'{HTTP_VECTOR}promt?query={mes}') as response:
        data = json.loads(response.text)

    text += data[0]['template'] + '\n' + data[1]['template'] + '\n' + data[2]['template']
    
    return text