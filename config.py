from dotenv import dotenv_values
import os

dotenv_values()

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'db')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)

API_KEY = os.getenv('API_KEY')
#API_KEY = os.getenv('API_KEY')
API_DEEPSEAK = os.getenv('API_DEEPSEAK')
DADATA_TOKEN = os.getenv('DADATA_TOKEN')
HTTP_1C = os.getenv('HTTP_1C')
HPPT_REDIS = os.getenv('HPPT_REDIS')