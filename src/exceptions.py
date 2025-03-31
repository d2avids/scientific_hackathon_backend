class NotFoundError(Exception):
    """Raise and handle this exception when related object not found in repo layer."""


class AlreadyExistsError(Exception):
    """Raise and handle this exception when related object already exists in repo layer."""
