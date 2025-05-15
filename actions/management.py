from datetime import datetime
from connections import execute_sql


def non_category(mes: dict):
    id_str = mes['id_str']
    id_int = mes['id_int']
    chatBot = mes['chatBot']

    query = """
        SELECT step 
        FROM ChatParameters 
        WHERE id_str = %s AND id_int = %s AND chat_bot = %s
    """
    params = (id_str, id_int, chatBot)
    row = execute_sql('select_one', query, params)

    # Проверяем, что row существует и содержит данные
    if row and isinstance(row, (list, tuple)) and len(row) > 0:
        step_value = row[0]

        if isinstance(step_value, str):  # Убедимся, что значение строки
            if 'non_category' in step_value:
                try:
                    # Попробуем извлечь дату
                    _, step_dt_str = step_value.split(';')
                    step_dt = datetime.strptime(step_dt_str, '%d.%m.%Y %H:%M:%S')
                    dt_now = datetime.now()
                    hours_passed = (dt_now - step_dt).total_seconds() / 3600

                    if hours_passed > 2:
                        dt_str = dt_now.strftime('%d.%m.%Y %H:%M:%S')
                        upd_query = """
                            UPDATE ChatParameters 
                            SET step = CONCAT('non_category;', %s) 
                            WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                        """
                        upd_params = (dt_str, id_str, id_int, chatBot)
                        execute_sql('update', upd_query, upd_params)
                        return 'Какой у Вас вопрос?'

                except (IndexError, ValueError) as e:
                    # Если формат неверный — сбросим шаг
                    execute_sql('update', """
                        UPDATE ChatParameters 
                        SET step = "disp" 
                        WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                    """, (id_str, id_int, chatBot))
                    return 'Передать диспетчеру'

            elif step_value == 'disp':
                return 'Передать диспетчеру'

    # Если нет данных или произошла ошибка — инициализируем шаг
    dt_now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    execute_sql('update', """
        UPDATE ChatParameters 
        SET step = CONCAT('non_category;', %s) 
        WHERE id_str = %s AND id_int = %s AND chat_bot = %s
    """, (dt_now, id_str, id_int, chatBot))

    return 'Какой у Вас вопрос?'