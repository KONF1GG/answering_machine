import mysql.connector
import config

def db_connextion():
    db_connection = mysql.connector.connect(
        user=config.MYSQL_USER, password=config.MYSQL_PASSWORD,
        host=config.MYSQL_HOST, port=config.MYSQL_PORT,
        database='calls'
        )
    return db_connection



