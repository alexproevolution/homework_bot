# Импорты из стандартных библиотек
import logging
import os
import sys
import time
from http import HTTPStatus

# Импорты сторонних библиотек
import requests
from dotenv import load_dotenv
from telebot import TeleBot, apihelper

# Импорты модулей этого проекта
from exceptions import (
    EndpointError,
    DataTypeError,
    ResponseFormatError,
    TokenError,
)


load_dotenv()

# Константы
CONNECTION_ERROR = '{error}, {url}, {headers}, {params}'
SERVICE_REJECTION = '{code}'
WRONG_ENDPOINT = (
    'Ошибка: {response_status}, '
    'Код ошибки: {error_code}, '
    'Сообщение: {error_message}, '
    'URL: {url}, '
    'Заголовки: {headers}, '
    'Параметры: {params}'
)
WRONG_HOMEWORK_STATUS = '{homework_status}'
WRONG_DATA_TYPE = 'Неверный тип данных {type}, вместо "dict"'
STATUS_IS_CHANGED = '{verdict}, {homework}'
STATUS_IS_NOT_CHANGED = 'Статус не изменился, нет записей'
FAILURE_TO_SEND_MESSAGE = '{error}, {message}'
GLOBAL_VARIABLE_IS_MISSING = 'Отсутствует глобальная переменная'
GLOBAL_VARIABLE_IS_EMPTY = 'Пустая глобальная переменная'
MESSAGE_IS_SENT = 'Сообщение {message} отправлено'
FORMAT_NOT_JSON = 'Формат не json {error}'
LIST_IS_EMPTY = 'Список пустой'

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
        (ENDPOINT, 'ENDPOINT'),
    )

    missing_tokens = []

    for token, name in tokens:
        if token is None or not token:
            missing_tokens.append(name)

    if missing_tokens:
        logging.critical(f'Отсутствуют токены: {", ".join(missing_tokens)}')
        raise TokenError(f'Отсутствуют токены: {", ".join(missing_tokens)}')


def send_message(bot, message):
    """Отправляет сообщение пользователю в Телегу."""
    logging.debug(f'Начало отправки сообщения в Telegram: {message}')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except (apihelper.ApiException,
            requests.exceptions.RequestException) as error:
        logging.info(f'Сообщение успешно отправлено: {message}')
        logging.error(f'Ошибка при отправке сообщения: {error}')
        return False

    return True


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    all_params = dict(url=ENDPOINT, headers=HEADERS, params=params)

    try:
        response = requests.get(**all_params)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(CONNECTION_ERROR.format(
            error=error,
            **all_params,
        ))

    response_status = response.status_code
    if response_status != HTTPStatus.OK:
        error_code, error_message = (
            (response.json().get('code', 'Неизвестный код'),
             response.json().get('error', 'Неизвестная ошибка'))
        )

        raise EndpointError(f'Ошибка: {response_status}, '
                            f'Код ошибки: {error_code}, '
                            f'Сообщение: {error_message}'
                            )

    try:
        return response.json()
    except Exception as error:
        raise ResponseFormatError(FORMAT_NOT_JSON.format(error))


def check_response(response):
    """Возвращает список домашних работ, если есть."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')

    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')

    homeworks = response['homeworks']

    if not isinstance(homeworks, list):
        raise TypeError('Значение ключа "homeworks" не является списком')

    return homeworks


def parse_status(homework):
    """Возвращает текст сообщения от ревьюера."""
    if not isinstance(homework, dict):
        raise DataTypeError(WRONG_DATA_TYPE.format(type(homework)))

    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(WRONG_HOMEWORK_STATUS.format(homework_status))

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if not homeworks:
                logging.debug('Список домашних работ пуст. '
                              'Статус не изменился.')
                continue

            homework = homeworks[0]
            message = parse_status(homework)

            if message != previous_message and send_message(bot, message):
                previous_message = message
                timestamp = response.get('current_date', timestamp)

        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.error(error_message)

            if (
                error_message != previous_message
                and send_message(bot, error_message)
            ):
                previous_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    log_file_path = os.path.join(os.path.expanduser('~'), 'homework_bot.log')
    logging.basicConfig(
        format='%(asctime)s, %(message)s, %(lineno)d, %(name)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    main()
