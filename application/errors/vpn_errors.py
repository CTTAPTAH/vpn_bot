"""
Ошибки, которые могут возникать на стороне VPN сервера.
Нужен, чтобы избавиться от зависимости исключений в инфраструктурном слое.
Gateway в инфраструктурном слое выбрасывает эти исключения, а ловит инфраструктурные исключения.
"""

class VpnClientAlreadyExistsError(Exception):
    """Клиент уже существует в VPN."""
    pass


class VpnKeyNotFoundError(Exception):
    """Клиент не найден в VPN."""
    pass


class VpnGatewayError(Exception):
    """Любая другая ошибка взаимодействия с VPN."""
    pass