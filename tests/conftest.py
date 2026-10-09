import os
import tempfile

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db_path}"
os.environ["DEMO_MODE"] = "true"
for _key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "RESEND_API_KEY", "BREVO_API_KEY", "BREVO_SENDER_EMAIL"):
    os.environ[_key] = ""

import pytest  # noqa: E402

from app.storage.database import get_session, init_db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    init_db()
    yield


@pytest.fixture()
def db_session():
    session = get_session()
    try:
        yield session
    finally:
        session.close()
