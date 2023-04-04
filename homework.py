import os
import requests

from dotenv import load_dotenv
import time
import telegram
import logging
from http import HTTPStatus
from exceptions import TokensException
import sys


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(level=logging.DEBUG, filename="py_log.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s",
                    encoding='utf-8')


def check_tokens():
    """Проверяем, все ли в порядке с токенами."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Проблема с токеном Практикума.')
        raise TokensException
    elif TELEGRAM_TOKEN is None:
        logging.critical('Проблема с токеном Телеграма.')
        raise TokensException
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('Проблема с id чата.')
        raise TokensException
    else:
        return True


def send_message(bot, message):
    """Сообщение о состоянии домашки отправляются владельцу."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        bot.send_message(chat_id, message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        logging.error(f'Проблема с отправкой сообщения. {error}')


def get_api_answer(timestamp):
    """Формируем запрос к серверу."""
    try:
        payload = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise requests.RequestException
        else:
            response = response.json()
            return response
    except Exception as error:
        logging.error(f'Проблемы с запросом. Возможно неправильно'
                      f'переданы параметры.{error}')
        raise Exception(f'Проблемы с запросом. Возможно неправильно'
                        f'переданы параметры. {error}')


def check_response(response):
    """Проверяем тип данных, полученных из ответа."""
    if not isinstance(response, dict):
        logging.error('Объект response не словарь')
        raise TypeError
    if 'current_date' not in response:
        logging.error('Нет ключа current_date')
        raise KeyError
    elif 'homeworks' not in response:
        logging.error('Нет ключа homeworks')
        raise KeyError
    else:
        homeworks = response.get('homeworks')
        if not isinstance(homeworks, list):
            logging.error('Объект homeworks не список')
            raise TypeError
        else:
            return homeworks


def parse_status(homework):
    """Извлекаем из ответа сервера нужные данные."""
    if 'status' not in homework:
        logging.error('Нет ключа "status" в ответе')
        raise KeyError
    elif 'homework_name' not in homework:
        logging.error('Нет ключа "homework_name" в ответе.')
        raise KeyError
    else:
        homework_status = homework['status']
        if homework_status not in HOMEWORK_VERDICTS:
            logging.error('Неизвестный статус работы')
            raise NameError
        else:
            verdict = HOMEWORK_VERDICTS[homework_status]
            homework_name = homework['homework_name']
            return (f'Изменился статус проверки работы "{homework_name}".'
                    f'{verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = requests.get(ENDPOINT, headers=HEADERS,
                                    params={'from_date': timestamp})
            response = response.json()
            homeworks = check_response(response)
            if homeworks == []:
                message = 'Статус работы не изменился.'
            else:
                homework = homeworks[0]
                message = parse_status(homework)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error('Сбой при отправке сообщения в телеграм.')
            print(message)
        finally:
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
