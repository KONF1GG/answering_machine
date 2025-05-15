import actions.action_functions as af
import core.conditions as con


def condition(mes, key):
    func = getattr(con, key, None)
    if callable(func):
        return func(mes)
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
        todo = data[key]['todo']

        if 'condition' in key:
            yes = data[key]['ifYes']
            no = data[key]['ifNo']
            if condition(mes, todo):
                key = yes
            else:
                key = no
            continue

        next_step = data[key]['next']

        if 'action' in key:
            if todo == 'empty':
                key = next_step
                continue
            elif todo == 'get_login':
                new_mes = af.get_login(mes)
                if new_mes['login'] != 'Null':
                    mes = new_mes
                    key = next_step
                else:
                    mes = new_mes
                    key = 'finish'
                continue
            else:
                func = getattr(af, todo, None)
                if callable(func):
                    func(mes)
                else:
                    raise AttributeError(f"Функция '{todo}' не найдена в 'af'")
                key = next_step
                continue

        key = next_step

    return 'end'
