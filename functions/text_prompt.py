import json
import requests
from functions import prompt_functions

REDIS = 'https://ws.freedom1.ru/redis/'

class Prompt:
    def __init__(self, login, schema):
        with requests.get(f'{REDIS}login:{login}') as response:
            self.data = json.loads(json.loads(response.text))

        with requests.get(f'{REDIS}scheme:{schema}') as response:
            self.scheme = json.loads(json.loads(response.text))

        with requests.get('http://192.168.111.61/UNF_FULL_WS/hs/Grafana/anydata?query=%D0%9F%D1%80%D0%BE%D0%BC%D1%82%D1%8B') as file:
            text = json.loads(file.text)
            text_dict = {}
            for value in text:
                name = value.get('name')
                template = value.get('template')
                text_dict[name] = template  # Исправлено: добавляем шаблоны по имени

        self.prompt_text = text_dict

        self.login = login

    def condition(self, key):
        if key == 'isAvans':
            return prompt_functions.isAvans(self.login)
        elif key == 'isBlocked':
            return prompt_functions.isBlocked(self.login)
        elif key == 'isFailure':
            return prompt_functions.isFailure(self.login)
        elif key == 'isIndexing':
            return prompt_functions.isIndexing(self.login)
        elif key == 'isInstallment':
            return prompt_functions.isInstallment(self.login)
        elif key == 'isGpon':
            return prompt_functions.isGpon(self.login)
        elif key == 'isDiscount':
            return prompt_functions.isDiscount(self.login)
        else:
            print(f'Function {key} not found')
        return False

    def start(self, key, text):
        if not key or key == 'finish':
            return text  # Возвращаем результат

        if key not in self.scheme:
            return text

        todo = self.scheme[key]['todo']

        if 'condition' in key:
            if todo in self.prompt_text:
                text += self.prompt_text[todo]

            yes = self.scheme[key]['ifYes']
            no = self.scheme[key]['ifNo']

            if self.condition(todo):
                return self.start(yes, text)
            else:
                return self.start(no, text)

        else:
            next_step = self.scheme[key]['next']
            if todo == 'empty':
                return self.start(next_step, text)
            else:
                if todo in self.prompt_text:
                    text += self.prompt_text[todo]
                return self.start(next_step, text)
