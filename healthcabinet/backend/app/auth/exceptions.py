class DuplicateEmailError(Exception):
    def __init__(self) -> None:
        super().__init__("Email already registered")


class InvalidCredentialsError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class AccountSuspendedError(Exception):
    def __init__(self) -> None:
        super().__init__("Account is suspended")
