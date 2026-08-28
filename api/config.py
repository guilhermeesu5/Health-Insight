from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    oracle_user: str = "ADMIN"
    oracle_password: str = ""
    oracle_dsn: str = ""
    oracle_wallet_dir: str = "./wallet"


settings = Settings()
