from app.platform.errors.domain_error import DomainError


class BackupEmAndamentoError(DomainError):
    status = 409
    code = "backup-em-andamento"
    title = "Backup já está em andamento"

    def __init__(self) -> None:
        super().__init__("Aguarde a conclusão do backup em andamento antes de iniciar outro.")
