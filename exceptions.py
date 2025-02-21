
class EndpointError(Exception):
    """Ошибка, если эндпойнт не корректен."""


class DataTypeError(Exception):
    """Ошибка, если тип данных не dict."""


class ResponseFormatError(Exception):
    """Ошибка, если формат response не json."""


class TokenError(Exception):
    """Исключение, возникающее при отсутствии токенов."""
