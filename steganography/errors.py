"""Excepções do StegoLab.

Todas herdam de ``StegoError`` e trazem uma mensagem em português, pronta a
ser mostrada ao utilizador (sem stack traces).
"""


class StegoError(Exception):
    """Erro base de todas as operações de esteganografia."""


class InvalidFileError(StegoError):
    """O ficheiro de cobertura não é válido ou o formato não é suportado."""


class InvalidImageError(InvalidFileError):
    """O ficheiro não é uma imagem válida ou suportada."""


class ToolMissingError(StegoError):
    """Falta uma ferramenta externa (FFmpeg, para vídeo)."""


class EmptyMessageError(StegoError):
    """A mensagem a esconder está vazia."""


class InvalidSecretError(StegoError):
    """O segredo (ficheiro ou data de validade) não é válido."""


class MessageTooLongError(StegoError):
    """A mensagem excede o limite máximo definido pela aplicação."""


class CapacityError(StegoError):
    """O ficheiro de cobertura não tem espaço suficiente para o segredo."""


class NoPayloadError(StegoError):
    """O ficheiro não contém o identificador StegoLab."""


class CorruptPayloadError(StegoError):
    """O cabeçalho foi encontrado, mas os dados estão truncados ou corrompidos."""


class PasswordRequiredError(StegoError):
    """A mensagem está encriptada e não foi fornecida palavra-passe."""


class WrongPasswordError(StegoError):
    """A palavra-passe não permite desencriptar a mensagem."""


class ExpiredMessageError(StegoError):
    """A data de validade do segredo já passou."""
