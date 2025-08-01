import logging
import re
import prompts.parametrs as params
import prompts.connection_parameters as cp

# Логгер
logger = logging.getLogger(__name__)


def extract_words(text: str, login: str):
    """
    Заменяет плейсхолдеры вида <name> в тексте значениями из объекта Abonent.

    Args:
        text (str): Исходный текст с плейсхолдерами (например, " <name> ").
        login (str): Логин абонента, для которого загружается объект Abonent.

    Returns:
        str: Текст с подставленными значениями. Если метод/поле не найдено — '<name>' заменяется на 'Неопознано'.
    """
    logger.info('extract_words', extra={'id_str': login, 'id_int': None})

    abon = params.Abonent(login)

    # Функция для замены одного вхождения <word>
    def replace_match(match):
        word = match.group(1)  # Получаем содержимое между <>
        try:
            attr = getattr(abon, word)
            if callable(attr):
                value = attr()
            else:
                value = attr  # Если это не метод, а свойство
            return str(value)
        except AttributeError:
            logger.debug(f'Поле или метод "{word}" не найдено у абонента', extra={'id_str': login, 'id_int': None})
            return 'Неопознано'
        except Exception as e:
            logger.error(f'Ошибка при обработке поля "{word}": {e}', extra={'id_str': login, 'id_int': None})
            return 'Неопознано'

    # Заменяем все вхождения <...>
    result = re.sub(r'<(.*?)>', replace_match, text)
    return result


def extract_connection_words(text: str, houseid: str):
    """
    Заменяет плейсхолдеры вида <name> в тексте значениями из объекта cp.

    Args:
        text (str): Исходный текст с плейсхолдерами (например, " <name> ").
        houseid (str): ID дома/абонента.

    Returns:
        str: Текст с подставленными значениями. Если метод/поле не найдено — '<name>' заменяется на 'Неопознано'.
    """
    
    # Функция для замены одного вхождения <word>
    def replace_match(match):
        word = match.group(1)  # Получаем содержимое между <>
        try:
            # Ищем функцию/метод по имени word в объекте cp
            func = getattr(cp, word)
            if callable(func):
                # Если это callable, вызываем с параметром houseid
                value = func(houseid)
                return str(value)
            else:
                # Если это не callable, возвращаем как есть
                return str(func)
        except (AttributeError, TypeError):
            return 'Неопознано'

    # Заменяем все вхождения <...>
    result = re.sub(r'<(.*?)>', replace_match, text)
    return result