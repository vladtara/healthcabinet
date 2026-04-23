class ProcessingError(Exception):
    def __init__(self, detail: str = "Processing error") -> None:
        self.detail = detail
        super().__init__(detail)
