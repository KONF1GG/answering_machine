import re
import prompts.parametrs as params

def extract_words(text: str, login: str):
    """
    Заменяет плейсхолдеры вида <name> в тексте значениями из объекта Abonent.

    Args:
        text (str): Исходный текст с плейсхолдерами (например, " <name> ").
        login (str): Логин абонента, для которого загружается объект Abonent.

    Returns:
        str: Текст с подставленными значениями. Если метод/поле не найдено — '<name>' заменяется на 'Неопознано'.
    """
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
            return 'Неопознано'
        except Exception as e:
            return 'Неопознано'

    # Заменяем все вхождения <...>
    result = re.sub(r'<(.*?)>', replace_match, text)
    return result