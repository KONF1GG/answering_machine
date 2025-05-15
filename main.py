from datetime import datetime, timedelta
import time
import json
import pytz

import requests

from config import HTTP_REDIS
from connections import execute_sql
from core.router import router


def get_message():
    #"""
    #Проверяет новые сообщения из БД за последние 5 минут, обновляет статус и 
    #запускает диалоговый роутер.
    #"""

    try:     
        tz = pytz.timezone('Asia/Yekaterinburg')     
        dt_5min = datetime.now(tz) - timedelta(minutes=5)
            
        query = '''
                select * from ChatStory join ChatParameters
                on ChatStory.id_int = ChatParameters.id_int and ChatStory.id_str = ChatParameters.id_str
                where ChatStory.ai_send = 0 and ChatStory.empl = 0 
                and ChatStory.dt > %s limit 1
            '''
        params = (dt_5min,)
        row = execute_sql('select_one', query, params)
            
        if row:

            id_str = row[0]
            mes = row[1]
            dt = row[2]
            messageId = row[3]
            id_int = row[4]
            login = row[13]
            chatBot = row[21]

            if mes == 'Очистить' and chatBot == 'Чат бот:Jivo Chat, токен:':
                del_query_story = 'delete from ChatStory where id_str = %s and id_int = %s and chat_bot = %s'
                del_query_param = 'delete from ChatParameters where id_str = %s and id_int = %s and chat_bot = %s'
                params = (id_str, id_int, chatBot)

                execute_sql('delete', del_query_story, params)
                execute_sql('delete', del_query_param, params)
                return

            mes_info = {
                'id_int': id_int,
                'id_str_sql': id_str,
                'id_str': id_str,
                'login': login,
                'messageId': messageId,
                'chatBot': chatBot,
                'text': mes,
                'dt': dt,
                'prompt': 'scheme:prompt'
            }

            query = 'update ChatStory set ai_send = 1, chat_bot = %s where messageId = %s'
            params = (chatBot, messageId)
            execute_sql('update', query, params)

            with requests.get(f'{HTTP_REDIS}scheme:petya') as response:
                data = json.loads(json.loads(response.text))
            #if id_int in [1036498173, 303455267]:
            router('start', mes_info, data)  
            time.sleep(5) 
        return

    except Exception as e:
        print(e)
        return
    

if __name__ == "__main__":
    while True:
        get_message()
else:
    print("Script is imported")
