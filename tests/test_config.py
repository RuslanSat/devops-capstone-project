"""Test database configuration for both CI and Kubernetes environments."""
import os
from pathlib import Path
import runpy
from unittest import TestCase
from unittest.mock import patch


CONFIG_PATH = Path(__file__).resolve().parents[1] / "service" / "config.py"


class TestConfiguration(TestCase):
    """Verify environment precedence without opening a database connection."""

    def test_explicit_database_uri_takes_precedence(self):
        """An explicit CI database URI must override component settings."""
        uri = "postgresql://ci-user:test-value@ci-database:5432/accounts"
        with patch.dict(
            os.environ,
            {"DATABASE_URI": uri, "DATABASE_HOST": "unused-host", "SECRET_KEY": "test-session-key"},
            clear=True,
        ):
            settings = runpy.run_path(str(CONFIG_PATH))
        self.assertEqual(settings["SQLALCHEMY_DATABASE_URI"], uri)
        self.assertEqual(settings["SECRET_KEY"], "test-session-key")
        self.assertFalse(settings["SQLALCHEMY_TRACK_MODIFICATIONS"])

    def test_default_database_configuration(self):
        """The local lab has predictable database defaults when no URI is set."""
        with patch.dict(os.environ, {}, clear=True):
            settings = runpy.run_path(str(CONFIG_PATH))
        self.assertEqual(
            settings["SQLALCHEMY_DATABASE_URI"],
            "postgresql://postgres:postgres@localhost:5432/postgres",
        )

    def test_database_components_from_kubernetes_environment(self):
        """Kubernetes host, user, database and disposable password are honored."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_HOST": "accounts-postgres",
                "DATABASE_USER": "lab-user",
                "DATABASE_PASSWORD": "disposable-test-value",
                "DATABASE_NAME": "accounts_test",
            },
            clear=True,
        ):
            settings = runpy.run_path(str(CONFIG_PATH))
        self.assertEqual(
            settings["SQLALCHEMY_DATABASE_URI"],
            "postgresql://lab-user:disposable-test-value@accounts-postgres:5432/accounts_test",
        )
