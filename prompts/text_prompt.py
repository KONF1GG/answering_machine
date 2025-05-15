import json

import requests

from config import HPPT_REDIS
from prompts import prompt_functions

class Prompt:
    def __init__(self, login, schema, mes):
        with requests.get(f'{HPPT_REDIS}login:{login}') as response:
            inner_json_str = json.loads(response.text)  # первый уровень
        
        if type(inner_json_str) is not dict:
            self.data = json.loads(inner_json_str)      # второй уровень
        else:
            self.data = inner_json_str

        with requests.get(f'{HPPT_REDIS}{schema}') as response:
            self.scheme = json.loads(json.loads(response.text))

        with requests.get(f'{HPPT_REDIS}scheme:prompt') as file:
            text = json.loads(json.loads(file.text))
            text_dict = {}
            for value in text:
                name = value.get('name')
                template = value.get('template')
                text_dict[name] = template  # Исправлено: добавляем шаблоны по имени

        self.prompt_text = text_dict

        self.login = login

        self.mes = mes

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
        elif key == 'isNotPayment':
            return prompt_functions.isNotPayment(self.login)
        elif key == 'IsPauseAndPayment':
            return prompt_functions.IsPauseAndPayment(self.login)
        elif key == 'isVisitScheduled':
            return prompt_functions.isVisitScheduled(self.login)
        elif key == 'isFutureVisit':
            return prompt_functions.isFutureVisit(self.login)
        elif key == 'isServise':
            return prompt_functions.isServise(self.login)
        elif key == 'isCamera':
            return prompt_functions.isCamera(self.login)
        elif key == 'isBlockedCamera':
            return prompt_functions.isBlockedCamera(self.login)
        elif key == 'isWired':
            return prompt_functions.isWired(self.login)
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
            
        elif todo == 'getDisp':
            return self.start('finish', 'to_disp')
        elif todo == 'getVector':
            next_step = self.scheme[key]['next']
            text_vector = prompt_functions.getVector(text, self.mes)
            return self.start(next_step, text_vector)

        else:
            next_step = self.scheme[key]['next']
            if todo == 'empty':
                return self.start(next_step, text)
            else:
                if todo in self.prompt_text:
                    text += self.prompt_text[todo]
                return self.start(next_step, text)
