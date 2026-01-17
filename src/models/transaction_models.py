"""
Pydantic models for transaction validation
Ensures all incoming data is properly validated before processing
"""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class TransactionInput(BaseModel):
    """
    Validated transaction input model

    All transactions must pass this validation before entering the fraud detection pipeline.
    This prevents malformed data from causing processing errors or producing invalid results.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required fields
    order_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique order identifier"
    )

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User identifier"
    )

    total_amount: Optional[float] = Field(
        default=None,
        gt=0.0,
        lt=1000000.0,
        description="Transaction amount in dollars (must be positive)"
    )

    payment_method: str = Field(
        ...,
        description="Payment method used"
    )

    account_age_days: int = Field(
        ...,
        ge=0,
        le=10000,
        description="Age of user account in days"
    )

    total_orders: int = Field(
        ...,
        ge=0,
        le=100000,
        description="Total number of orders by this user"
    )

    # Optional fields
    avg_order_value: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        lt=1000000.0,
        description="Average order value for this user"
    )

    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,  # IPv6 max length
        description="IP address of the user"
    )

    # Allow legacy 'amount' field as alias
    amount: Optional[float] = Field(default=None, exclude=True)

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order_id format"""
        if not v or v.strip() == '':
            raise ValueError('order_id cannot be empty')

        # Allow flexible order_id format but prevent SQL injection patterns
        if any(sql_keyword in v.upper() for sql_keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', ';--']):
            raise ValueError('order_id contains invalid characters')

        return v.strip()

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id format"""
        if not v or v.strip() == '':
            raise ValueError('user_id cannot be empty')

        # Prevent SQL injection
        if any(sql_keyword in v.upper() for sql_keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', ';--']):
            raise ValueError('user_id contains invalid characters')

        return v.strip()

    @field_validator('payment_method')
    @classmethod
    def normalize_payment_method(cls, v: str) -> str:
        """Normalize payment method to lowercase and validate"""
        normalized = v.lower().strip()
        valid_methods = ['credit_card', 'debit_card', 'bank_transfer', 'paypal', 'crypto']

        if normalized not in valid_methods:
            raise ValueError(
                f"payment_method must be one of: {', '.join(valid_methods)}"
            )

        return normalized

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address format (basic validation)"""
        if v is None or v == '':
            return None

        v = v.strip()

        # Basic IPv4 validation
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # Basic IPv6 validation (simplified)
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'

        if re.match(ipv4_pattern, v):
            # Validate IPv4 octets are 0-255
            octets = v.split('.')
            if all(0 <= int(octet) <= 255 for octet in octets):
                return v
        elif re.match(ipv6_pattern, v):
            return v

        # If validation fails, return None rather than raising error
        # (IP address is optional and may have various formats)
        return None

    def model_post_init(self, __context) -> None:
        """Post-initialization: handle legacy 'amount' field and validate total_amount"""
        # If 'amount' was provided but not 'total_amount', use 'amount'
        if self.total_amount is None:
            if self.amount is not None:
                self.total_amount = self.amount
            else:
                raise ValueError("Either 'total_amount' or 'amount' must be provided")

        # Validate total_amount is positive
        if self.total_amount <= 0:
            raise ValueError("total_amount must be greater than 0")


class FraudDetectionResult(BaseModel):
    """Validated fraud detection result"""

    order_id: str
    fraud_score: float = Field(ge=0.0, le=1.0)
    ml_score: float = Field(ge=0.0, le=1.0)
    velocity_boost: float = Field(ge=0.0, le=1.0)
    redis_boost: float = Field(ge=0.0, le=1.0)
    qdrant_boost: float = Field(ge=0.0, le=1.0)
    recommendation: Literal['APPROVE', 'MANUAL_REVIEW', 'AGENT_ANALYSIS', 'BLOCK']
    processing_time_seconds: float = Field(gt=0.0)
    agent_analysis: Optional[dict] = None
    redis_context: list = Field(default_factory=list)
    qdrant_similar_cases: int = Field(ge=0)


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: Literal['healthy', 'degraded', 'unhealthy']
    timestamp: datetime
    components: dict
    metrics: Optional[dict] = None


class ValidationError(BaseModel):
    """Validation error response"""

    error: str
    field: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
