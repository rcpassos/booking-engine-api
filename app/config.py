from pydantic import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str
    jwt_secret_key: str
    jwt_expire_minutes: int = 60
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    smtp_from_email: str

    class Config:
        env_file = ".env"


settings = Settings()
