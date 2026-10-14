"""Excepções do StegoLab.

Todas herdam de ``StegoError`` e trazem uma mensagem em português, pronta a
ser mostrada ao utilizador (sem stack traces).
"""


class StegoError(Exception):
    """Erro base de todas as operações de esteganografia."""


class InvalidImageError(StegoError):
    """O ficheiro não é uma imagem válida ou suportada."""


class EmptyMessageError(StegoError):
    """A mensagem a esconder está vazia."""


class MessageTooLongError(StegoError):
    """A mensagem excede o limite máximo definido pela aplicação."""


class CapacityError(StegoError):
    """A imagem não tem píxeis suficientes para guardar a mensagem."""


class NoPayloadError(StegoError):
    """A imagem não contém o identificador StegoLab."""


class CorruptPayloadError(StegoError):
    """O cabeçalho foi encontrado, mas os dados estão truncados ou corrompidos."""


class PasswordRequiredError(StegoError):
    """A mensagem está encriptada e não foi fornecida palavra-passe."""


class WrongPasswordError(StegoError):
    """A palavra-passe não permite desencriptar a mensagem."""
