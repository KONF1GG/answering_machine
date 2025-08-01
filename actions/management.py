from datetime import datetime
from connections import execute_sql
import pytz
import json

import logging
import json

logger = logging.getLogger(__name__)


def non_category(mes: dict):
    tz = pytz.timezone('Asia/Yekaterinburg')      
    id_str = mes['id_str']
    id_int = mes['id_int']
    chatBot = mes['chatBot']


    logging.info('non_category', extra={'id_str':id_str, 'id_int':id_int})


    query = """
        SELECT step 
        FROM ChatParameters 
        WHERE id_str = %s AND id_int = %s AND chat_bot = %s
    """
    params = (id_str, id_int, chatBot)
    row = execute_sql('select_one', query, params)


    if row[0] and 'non_category' in row[0]:
        if row[0] != 'non_category':
            dt = datetime.now(tz)
            dt_str = dt.strftime('%d.%m.%Y %H:%M:%S')
            step_dt_str = row[0].split(';')[1]
            step_dt = datetime.strptime(step_dt_str, '%d.%m.%Y %H:%M:%S').replace(tzinfo=tz)
            difference = dt - step_dt
            hours_difference = difference.total_seconds() / 3600

            if hours_difference > 2:
                upd_query = """
                        UPDATE ChatParameters 
                        SET step = CONCAT('non_category;', %s) 
                        WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                    """
                upd_params = (dt_str, id_str, id_int, chatBot)
                execute_sql('update', upd_query, upd_params)

                return 'Здравствуйте! Чем могу помочь?'

            else:
                execute_sql('update', """
                    UPDATE ChatParameters 
                    SET step = "disp" 
                    WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                    """, (id_str, id_int, chatBot))

                return 'Передать диспетчеру'

        else:
            execute_sql('update', """
                    UPDATE ChatParameters 
                    SET step = "disp" 
                    WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                    """, (id_str, id_int, chatBot))

            return 'Передать диспетчеру'

    else:
        
        dt_now = datetime.now(tz).strftime('%d.%m.%Y %H:%M:%S')

        execute_sql('update', """
                UPDATE ChatParameters 
                SET step = CONCAT('non_category;', %s) 
                WHERE id_str = %s AND id_int = %s AND chat_bot = %s
                """, (dt_now, id_str, id_int, chatBot))

        return 'Здравствуйте! Чем могу помочь?'


def failure_sql(mes, failure_text):
    id_int = mes['id_int']
    id_str = mes['id_str']
    chatBot = mes['chatBot']
    dt = mes['dt']
    login = mes['login']

    delete_failure_query = '''
                        DELETE FROM failure_message 
                        WHERE id_int = %s AND id_str = %s AND chat_bot = %s
                    '''
    params_delete_failure = (id_int, id_str, chatBot)
    execute_sql('delete', delete_failure_query, params_delete_failure)

    failure_data = json.loads(failure_text)
    failure_code = list(failure_data.keys())[0].split(':')[1]
    
    insert_failure_query = '''
                        INSERT INTO failure_message
                        (id_str, id_int, failure, dt, login, chat_bot)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    '''
    
    ins_params = (id_str, id_int, failure_code, dt, login, chatBot)

    execute_sql('insert', insert_failure_query, ins_params)