class HealthValueNotFoundError(Exception):
    def __init__(self, detail: str = "Health value not found") -> None:
        self.detail = detail
        super().__init__(detail)
