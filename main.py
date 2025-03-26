import requests
import json
from connections import db_connextion
from way import start
import time
from datetime import datetime, timedelta



def get_message():
    try:        
        dt_now = datetime.now() - timedelta(seconds=15)
        dt_for_select = dt_now.strftime('%Y-%m-%d %H:%M:%S')

        db_connection = db_connextion()
        cur = db_connection.cursor(buffered=True)
        cur.execute(f'''
                select * from ChatStory join ChatParameters
                on ChatStory.id_int = ChatParameters.id_int and ChatStory.id_str = ChatParameters.id_str
                where ChatStory.ai_send = 0 and ChatStory.empl = 0 
                and ChatStory.dt < "{dt_for_select}" limit 1
            ''')
        row = cur.fetchone()
        db_connection.close()
            
        if row:
            print(row)
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            id_str = row[0]
            mes = row[1]
            dt = row[2]
            messageId = row[3]
            id_int = row[4]
            empl = row[5]
            login = row[13]
            chatBot = row[21]

            if mes == 'Очистить' and chatBot == 'Чат бот:Jivo Chat, токен:':
                db_connection = db_connextion()
                upd = db_connection.cursor(buffered=True)
                upd.execute(f'''
                        delete from ChatStory where id_str = "{id_str}" and id_int = {id_int} and chat_bot = "{chatBot}"
                    ''')
                db_connection.commit()

                upd1 = db_connection.cursor(buffered=True)
                upd1.execute(f'''
                        delete from ChatParameters where id_str = "{id_str}" and id_int = {id_int} and chat_bot = "{chatBot}";
                    ''')
                db_connection.commit()
                
                db_connection.close()
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
            }

            db_connection = db_connextion()
            upd = db_connection.cursor(buffered=True)
            upd.execute(f'''
                    update ChatStory set ai_send = 1, chat_bot = "{chatBot}" where messageId = "{messageId}"
                ''')
            db_connection.commit()
            db_connection.close()

            with requests.get(f'https://ws.freedom1.ru/redis/scheme:petya') as response:
                data = json.loads(json.loads(response.text))
            #if id_int in [1036498173, 303455267]:
            print(mes)
            start('start', mes_info, data)  
            time.sleep(5) 
        return

    except Exception as e:
        print(f'\n Ошибка где-то вылезла: {e}')
        return
    

    
if __name__ == "__main__":
    print('START')
    while True:
        get_message()

else:
    print("Script is imported")
