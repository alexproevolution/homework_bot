class NetworkError(Exception):
    """Ошибка отсутствия сети."""


class EndpointError(Exception):
    """Ошибка, если эндпойнт не корректен."""


class MessageSendingError(Exception):
    """Ошибка отправки сообщения."""


class GlobalsError(Exception):
    """Ошибка, если есть пустые глобальные переменные."""


class DataTypeError(Exception):
    """Ошибка, если тип данных не dict."""


class ResponseFormatError(Exception):
    """Ошибка, если формат response не json."""


class TokenError(Exception):
    """Исключение, возникающее при отсутствии токенов."""
