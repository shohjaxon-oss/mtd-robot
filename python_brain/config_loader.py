"""Configuration loader and schema validator using Pydantic v2.

Enforces zero-tolerance validation for capital protection and risk limits.
"""

from pathlib import Path
from typing import List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "mtd-robot"
    version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    timezone: str = "UTC"


class MT5SystemConfig(BaseModel):
    timeout_ms: int = Field(default=60000, ge=5000, le=300000)
    portable: bool = False
    reconnect_retries: int = Field(default=3, ge=1, le=10)
    reconnect_delay_seconds: int = Field(default=5, ge=1, le=60)


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_to_console: bool = True
    log_to_file: bool = True
    file_path: str = "logs/trading.log"
    rotation: str = "10 MB"
    retention: str = "30 days"
    compression: str = "zip"
    mask_secrets: bool = True


class BridgeConfig(BaseModel):
    protocol: str = "zmq"
    host: str = "127.0.0.1"
    heartbeat_interval_seconds: float = Field(default=1.0, gt=0.0)
    heartbeat_timeout_seconds: float = Field(default=5.0, gt=0.0)


class SafetyConfig(BaseModel):
    allow_live: bool = Field(default=False, description="Strict safety guard: False for Demo only, True for Live")


class SettingsConfig(BaseModel):
    app: AppConfig
    mt5: MT5SystemConfig
    logging: LoggingConfig
    bridge: BridgeConfig
    safety: SafetyConfig = Field(default_factory=SafetyConfig)


# --------------------------------------------------------------------------
# RISK CONFIGURATION (Strict Rules)
# --------------------------------------------------------------------------
class PerTradeRiskConfig(BaseModel):
    risk_per_trade_pct: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Risk per trade in percentage (Strictly max 1.0%)",
    )
    max_allowed_risk_per_trade_pct: float = Field(default=1.0, le=1.0)
    require_stop_loss: bool = Field(
        default=True,
        description="Stop loss is strictly mandatory across all positions.",
    )

    @field_validator("require_stop_loss")
    @classmethod
    def validate_sl_mandatory(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "VIOLATION: require_stop_loss MUST be True! Trading without SL is strictly forbidden."
            )
        return v

    @field_validator("risk_per_trade_pct")
    @classmethod
    def validate_risk_pct(cls, v: float) -> float:
        if v > 1.0:
            raise ValueError(
                f"VIOLATION: risk_per_trade_pct ({v}%) exceeds maximum hard limit of 1.0%!"
            )
        return v


class DrawdownLimitsConfig(BaseModel):
    daily_loss_limit_pct: float = Field(default=2.0, gt=0.0, le=3.0)
    weekly_loss_limit_pct: float = Field(default=4.0, gt=0.0, le=6.0)
    max_drawdown_kill_switch_pct: float = Field(default=12.0, gt=0.0, le=15.0)


class ExecutionLimitsConfig(BaseModel):
    max_open_positions: int = Field(default=1, ge=1, le=3)
    max_daily_trades: int = Field(default=5, ge=1, le=20)
    consecutive_losses_cooldown_trades: int = Field(default=3, ge=1)
    cooldown_duration_minutes: int = Field(default=60, ge=5)
    max_spread_points: float = Field(default=40.0, gt=0.0)
    min_risk_reward_ratio: float = Field(default=1.5, ge=1.0)


class ForbiddenMechanicsConfig(BaseModel):
    allow_martingale: bool = False
    allow_grid: bool = False
    allow_averaging_down: bool = False

    @model_validator(mode="after")
    def verify_no_toxic_mechanics(self) -> "ForbiddenMechanicsConfig":
        if self.allow_martingale:
            raise ValueError("VIOLATION: Martingale is strictly prohibited by system constitution!")
        if self.allow_grid:
            raise ValueError("VIOLATION: Grid trading is strictly prohibited by system constitution!")
        if self.allow_averaging_down:
            raise ValueError(
                "VIOLATION: Averaging-down is strictly prohibited by system constitution!"
            )
        return self


class RiskConfig(BaseModel):
    per_trade_risk: PerTradeRiskConfig
    drawdown_limits: DrawdownLimitsConfig
    execution_limits: ExecutionLimitsConfig
    forbidden_mechanics: ForbiddenMechanicsConfig
    strategy_profiles: dict = Field(default_factory=dict)


# --------------------------------------------------------------------------
# SYMBOL CONFIGURATION
# --------------------------------------------------------------------------
class TradeSession(BaseModel):
    name: str
    start_utc: str
    end_utc: str


class ScheduleConfig(BaseModel):
    timezone: str = "UTC"
    avoid_weekend_close_minutes: int = Field(default=60, ge=0)
    avoid_market_open_minutes: int = Field(default=30, ge=0)
    trade_sessions: List[TradeSession] = []


class ExecutionConfig(BaseModel):
    max_slippage_points: int = Field(default=30, ge=1)
    magic_number: int = Field(default=777101, ge=1)
    order_comment: str = "MTD-Robot-v1"


class SymbolDetailsConfig(BaseModel):
    base_symbol: str = "XAUUSD"
    description: str = "Gold vs US Dollar (OTC Spot)"
    candidate_symbols: List[str] = Field(default_factory=lambda: ["XAUUSD", "XAUUSDm", "XAUUSD.c"])
    expected_contract_size: float = Field(default=100.0, gt=0.0)
    primary_timeframe: str = "M5"
    supported_timeframes: List[str] = ["M1", "M5", "M15", "H1", "H4", "D1"]
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


class SymbolsConfig(BaseModel):
    symbol: SymbolDetailsConfig

    @property
    def primary_symbol(self) -> str:
        return self.symbol.base_symbol


# --------------------------------------------------------------------------
# ENVIRONMENT VARIABLES CONFIGURATION (.env)
# --------------------------------------------------------------------------
class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MT5_LOGIN: Optional[int] = None
    MT5_PASSWORD: Optional[str] = None
    MT5_SERVER: Optional[str] = None
    MT5_PATH: Optional[str] = None
    MT5_TIMEOUT_MS: int = 60000
    MT5_PORTABLE: bool = False

    ACCOUNT_TYPE: str = "demo"
    ACCOUNT_TIER: str = "standard"
    PRIMARY_SYMBOL: str = "XAUUSD"

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    ZMQ_PUB_PORT: int = 5555
    ZMQ_REP_PORT: int = 5556


# --------------------------------------------------------------------------
# GLOBAL AGGREGATE CONFIG
# --------------------------------------------------------------------------
class GlobalConfig(BaseModel):
    settings: SettingsConfig
    risk: RiskConfig
    symbols: SymbolsConfig
    env: EnvConfig


def load_yaml_file(filepath: Path) -> dict:
    """Safely load and parse YAML file."""
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found at: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Config file {filepath} is empty!")
    return data


def load_all_configs(
    config_dir: str = "config",
    env_file: Optional[str] = ".env",
) -> GlobalConfig:
    """Load, merge, and strictly validate all project configurations."""
    c_path = Path(config_dir)

    settings_data = load_yaml_file(c_path / "settings.yaml")
    risk_data = load_yaml_file(c_path / "risk.yaml")
    symbols_data = load_yaml_file(c_path / "symbols.yaml")

    settings_obj = SettingsConfig(**settings_data)
    risk_obj = RiskConfig(**risk_data)
    symbols_obj = SymbolsConfig(**symbols_data)

    if env_file:
        load_dotenv(env_file, override=False)
    env_obj = EnvConfig(_env_file=env_file if env_file and Path(env_file).exists() else None)

    return GlobalConfig(
        settings=settings_obj,
        risk=risk_obj,
        symbols=symbols_obj,
        env=env_obj,
    )
