class DocumentNotFoundError(Exception):
    def __init__(self, detail: str = "Document not found") -> None:
        self.detail = detail
        super().__init__(detail)


class UploadLimitExceededError(Exception):
    def __init__(self, detail: str = "Daily upload limit reached — try again tomorrow") -> None:
        self.detail = detail
        super().__init__(detail)


class DocumentRetryNotAllowedError(Exception):
    def __init__(
        self,
        detail: str = "Retry is only allowed for documents in partial or failed status",
    ) -> None:
        self.detail = detail
        super().__init__(detail)


class DocumentYearConfirmationNotAllowedError(Exception):
    """Raised when confirm-date-year is called on a document that does not need it."""

    def __init__(
        self,
        detail: str = "Document does not require year confirmation",
    ) -> None:
        self.detail = detail
        super().__init__(detail)


class DocumentYearConfirmationInvalidError(Exception):
    """Raised when the supplied year cannot resolve the stored partial date text."""

    def __init__(self, detail: str = "Invalid year for document partial date") -> None:
        self.detail = detail
        super().__init__(detail)
