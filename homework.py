import os
import sys
import time
import logging
import json

from dotenv import load_dotenv
import requests
import telegram
from http import HTTPStatus


load_dotenv()


PRACTICUM_TOKEN = os.getenv('TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
TOKENS_NAME = {
    'Практикум': PRACTICUM_TOKEN,
    'телеграм': TELEGRAM_TOKEN,
    'chat_id': TELEGRAM_CHAT_ID
}

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
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    for key, val in TOKENS_NAME.items():
        if val is None:
            logging.critical(f'Отсутствует токен {key}')
    logging.critical('Проблемы с токенами')
    return False


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
        if response.status_code == HTTPStatus.OK:
            response = response.json()
            return response
        raise ConnectionError(('Ошибка соединения'))
    except requests.RequestException:
        raise ConnectionError('Ошибка при обращении к внешнему API')
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout('Превышено время ожидания')
    except requests.exceptions.HTTPError:
        raise requests.exceptions.HTTPError('Ошибка HTTP')
    except json.JSONDecodeError:
        raise json.JSONDecodeError('Объект response не является json')


def check_response(response):
    """Проверяем тип данных, полученных из ответа."""
    if not isinstance(response, dict):
        raise TypeError('Объект response не словарь')
    if 'current_date' not in response:
        raise KeyError('Нет ключа current_date')
    if 'homeworks' not in response:
        raise KeyError('Нет ключа homeworks')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Объект homeworks не список')
    return homeworks


def parse_status(homework):
    """Извлекаем из ответа сервера нужные данные."""
    if not isinstance(homework, dict):
        raise TypeError('Объект homework не словарь')
    if 'status' not in homework:
        raise KeyError('Нет ключа "status" в ответе')
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_name" в ответе.')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Неизвестный статус работы {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    homework_name = homework['homework_name']
    return (f'Изменился статус проверки работы "{homework_name}".{verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Проблемы с токенами')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks == []:
                message = 'Статус работы не изменился.'
            else:
                homework = homeworks[0]
                message = parse_status(homework)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        send_message(bot, message)
        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
