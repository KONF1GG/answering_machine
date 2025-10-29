# config.py
from dotenv import load_dotenv
import os

load_dotenv()  # ← это загружает .env в os.environ

MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')  # порт — строка или int?

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