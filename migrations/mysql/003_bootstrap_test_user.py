"""Ensure the live test user exists with admin access."""

import os

import bcrypt


TEST_USER_EMAIL = "takurajunia@gmail.com"
TEST_USER_NAME = "Takura Junia"
TEST_USER_ROLE = "admin"
PASSWORD_ENV_NAME = "BOOTSTRAP_TEST_USER_PASSWORD"


def run(connection, release_dir) -> None:
    password = os.environ.get(PASSWORD_ENV_NAME, "")
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (TEST_USER_EMAIL,),
        )
        user = cursor.fetchone()

        if not password and not user:
            raise RuntimeError(
                f"{PASSWORD_ENV_NAME} is required to create {TEST_USER_EMAIL}"
            )

        if password:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if user:
                cursor.execute(
                    """
                    UPDATE users
                    SET name=%s, role=%s, is_active=%s, password_hash=%s
                    WHERE id=%s
                    """,
                    (TEST_USER_NAME, TEST_USER_ROLE, True, password_hash, user["id"]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (email, name, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (TEST_USER_EMAIL, TEST_USER_NAME, password_hash, TEST_USER_ROLE, True),
                )
            return

        cursor.execute(
            """
            UPDATE users
            SET name=%s, role=%s, is_active=%s
            WHERE id=%s
            """,
            (TEST_USER_NAME, TEST_USER_ROLE, True, user["id"]),
        )
    finally:
        cursor.close()
