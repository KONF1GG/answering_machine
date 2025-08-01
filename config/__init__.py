from dotenv import dotenv_values
import os

dotenv_values()

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'db')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)

#API_KEY = os.getenv('API_KEY')
API_KEY = os.getenv('API_KEY')
API_DEEPSEAK = os.getenv('API_DEEPSEAK')
API_GPT = os.getenv('api-gpt')

DADATA_TOKEN = os.getenv('DADATA_TOKEN')

PROXY = os.getenv('proxy')

HTTP_1C = os.getenv('HTTP_1C')
HTTP_REDIS = os.getenv('HPPT_REDIS')
HTTP_VECTOR = os.getenv('HTTP_VECTOR')
HTTP_61 = os.getenv('HTTP_61')
HTTP_ADDRESS = os.getenv('HTTP_ADDRESS')