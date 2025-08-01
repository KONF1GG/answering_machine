import actions.action_functions as af
import core.conditions as con
import logging


logger = logging.getLogger(__name__)


def condition(mes, key):
    logging.info(f'condition {key}')
    func = getattr(con, key, None)
    if callable(func):
        return func(mes)
    else:
        logging.debug(f'Function {key} not found')
    return False


def router(key: str, mes: dict, data: dict):
    """
    Обрабатывает диалог/сценарий по шагам на основе переданных данных.

    Args:
        key (str): Начальный ключ для выбора шага.
        mes (dict): Сообщение и данные пользователя.
        data (dict): Структура с шагами сценария. Каждый шаг содержит:
            - 'todo': действие для выполнения
            - 'next': следующий шаг
            - 'ifYes' и 'ifNo': шаги при условии (если есть)

    Returns:
        str: Статус завершения — всегда возвращает 'end'.

    Raises:
        AttributeError: Если указана несуществующая функция в 'todo'.
    """
    
    while key and key != 'finish':
        if key not in data:
            break

        step = data[key]
        todo = step.get('todo')

        logging.info(f'! ! ! ! {key} ! ! ! !')
        if 'condition' in key:
            yes = step.get('ifYes')
            no = step.get('ifNo')
            if condition(mes, todo):
                key = yes
            else:
                key = no
            continue

        next_step = data[key]['next']

        if 'action' in key:
            if todo == 'empty':
                key = step.get('next', 'finish')
            elif todo == 'get_login':
                new_mes = af.get_login(mes)
                if new_mes.get('login') != 'Null':
                    mes = new_mes
                key = step.get('next', 'finish')
            elif todo == 'get_houseId':
                new_mes = af.get_houseId(mes)
                if new_mes.get('login') != 'Null':
                    mes = new_mes
                    key = step.get('next', 'finish')
                else:
                    key = 'finish'
            else:
                func = getattr(af, todo, None)
                if callable(func):
                    func(mes)
                else:
                    raise AttributeError(f"Функция '{todo}' не найдена")
                key = step.get('next', 'finish')
            continue

        key = step.get('next', 'finish')

    return 'end'
