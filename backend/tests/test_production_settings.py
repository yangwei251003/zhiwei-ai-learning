from app.core import Settings


def test_settings_split_configured_cors_origins():
    settings = Settings(
        secret_key="test-secret",
        cors_origins="https://zhiwei.vercel.app, https://www.zhiwei.example",
    )

    assert settings.cors_origins_list == [
        "https://zhiwei.vercel.app",
        "https://www.zhiwei.example",
    ]
