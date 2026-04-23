from unittest.mock import call, patch

from app.core.database import import_orm_models


def test_import_orm_models_imports_all_model_modules() -> None:
    with patch("app.core.database.import_module") as mock_import_module:
        import_orm_models()

    assert mock_import_module.call_args_list == [
        call("app.admin.models"),
        call("app.ai.models"),
        call("app.auth.models"),
        call("app.billing.models"),
        call("app.documents.models"),
        call("app.health_data.models"),
        call("app.users.models"),
    ]
