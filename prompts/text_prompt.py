import logging
import json
import requests

from config import HTTP_REDIS
from prompts import prompt_functions, vectors

# Логгер
logger = logging.getLogger(__name__)


class Prompt:
    def __init__(self, login, schema, mes):
        logger.info('__init__', extra={'login': login})
        self.login = login
        self.mes = mes

        if login != '':
            with requests.get(f'{HTTP_REDIS}login:{login}') as response:
                inner_json_str = json.loads(response.text)  # первый уровень

            if isinstance(inner_json_str, str):
                self.data = json.loads(inner_json_str)  # второй уровень
            else:
                self.data = inner_json_str
        else:
            self.data = {}

        with requests.get(f'{HTTP_REDIS}{schema}') as response:
            self.scheme = json.loads(json.loads(response.text))

        with requests.get(f'{HTTP_REDIS}scheme:prompt') as file:
            raw_data = json.loads(json.loads(file.text))
            self.prompt_text = {item['name']: item['template'] for item in raw_data if 'name' in item and 'template' in item}

    def condition(self, key):

        logger.info('condition', extra={'login': self.login})
        try:
            if key == 'isAvans':
                return prompt_functions.isAvans(self.login)
            elif key == 'isBlocked':
                return prompt_functions.isBlocked(self.login)
            elif key == 'isFailure':
                return prompt_functions.isFailure(self.login, self.mes)
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
            elif key == 'isWireless':
                return prompt_functions.isWireless(self.login)
            elif key == 'isInternet':
                return prompt_functions.isInternet(self.login)
            elif key == 'isBlockedIntercom':
                return prompt_functions.isBlockedIntercom(self.login)
            elif key == 'isIntercom':
                return prompt_functions.isIntercom(self.login)
            elif key == 'isSibay':
                return prompt_functions.isSibay(self.login)
            elif key == 'isAbon':
                return prompt_functions.isAbon(self.login)
            else:
                logger.warning(f'Функция {key} не найдена', extra={'login': self.login})
                return False
        except Exception as e:
            logger.error(f'Ошибка в condition: {e}', extra={'login': self.login})
            return False

    def start(self, key, text):
        logger.info('start', extra={'login': self.login})
        try:
            if not key or 'finish' in key:
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
            elif todo == 'getVector_one':
                next_step = self.scheme[key]['next']
                text_vector = vectors.getVector(text, self.mes)
                return self.start(next_step, text_vector)
            elif todo == 'getVector_two':
                next_step = self.scheme[key]['next']
                text_vector = vectors.getVector(text, self.mes)
                return self.start(next_step, text_vector)
            elif todo == 'getVector_three':
                next_step = self.scheme[key]['next']
                text_vector = vectors.getVector(text, self.mes)
                return self.start(next_step, text_vector)
            elif todo == 'getVector':
                next_step = self.scheme[key]['next']
                text_vector = vectors.getVector(text, self.mes)
                return self.start(next_step, text_vector)

            else:
                next_step = self.scheme[key]['next']
                if todo == 'empty':
                    return self.start(next_step, text)
                else:
                    if todo in self.prompt_text:
                        text += self.prompt_text[todo]
                    return self.start(next_step, text)
        except Exception as e:
            logger.error(f'Ошибка в start: {e}', extra={'login': self.login})
            return text