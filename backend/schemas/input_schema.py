"""Pydantic schemas for input validation."""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

class JurisdictionEnum(str, Enum):
    """Supported jurisdictions."""
    INDIA = "India"
    US = "US"

class EntityTypeEnum(str, Enum):
    """Entity types."""
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    SERVICE_PROVIDER = "service_provider"
    R_AND_D = "r_and_d"
    CONTRACT_MANUFACTURER = "contract_manufacturer"

class TransactionTypeEnum(str, Enum):
    """Transaction types."""
    SERVICES = "services"
    GOODS = "goods"
    LOANS = "loans"
    GUARANTEES = "guarantees"
    IP_LICENSING = "IP"
    COST_SHARING = "cost_sharing"

class RiskLevelEnum(str, Enum):
    """Risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class CompanyInput(BaseModel):
    """Schema for company input data."""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    jurisdiction: JurisdictionEnum = Field(..., description="Company jurisdiction")
    tax_id: str = Field(..., min_length=1, max_length=100, description="Tax identification number")
    entity_type: EntityTypeEnum = Field(..., description="Type of entity")
    address: Optional[str] = Field(None, description="Company address")
    industry: Optional[str] = Field(None, max_length=100, description="Industry sector")
    fiscal_year_end: Optional[str] = Field(None, pattern=r"^\d{2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$", description="Fiscal year end (e.g., 31-Mar)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "TechCorp India Pvt Ltd",
                "jurisdiction": "India",
                "tax_id": "AAACT1234A",
                "entity_type": "service_provider",
                "address": "123 Tech Park, Bangalore",
                "industry": "Information Technology",
                "fiscal_year_end": "31-Mar"
            }
        }

class FunctionalProfile(BaseModel):
    """Schema for functional analysis."""
    functions: List[str] = Field(..., min_items=1, description="List of functions performed")
    assets: List[str] = Field(..., min_items=1, description="List of assets used")
    risks: List[str] = Field(..., min_items=1, description="List of risks assumed")
    risk_level: RiskLevelEnum = Field(..., description="Overall risk level")
    
    @validator('functions', 'assets', 'risks')
    def check_not_empty_strings(cls, v):
        """Ensure list items are not empty strings."""
        if any(not item.strip() for item in v):
            raise ValueError('List items cannot be empty strings')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "functions": [
                    "Software development",
                    "Quality assurance",
                    "Customer support"
                ],
                "assets": [
                    "Employee skills",
                    "Development infrastructure",
                    "Customer databases"
                ],
                "risks": [
                    "Market risk (low)",
                    "Credit risk (low)",
                    "Operational risk (medium)"
                ],
                "risk_level": "low"
            }
        }

class TransactionInput(BaseModel):
    """Schema for transaction input data."""
    company_id: int = Field(..., gt=0, description="ID of the company")
    transaction_type: TransactionTypeEnum = Field(..., description="Type of transaction")
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed description")
    related_party_name: str = Field(..., min_length=1, max_length=255, description="Related party name")
    related_party_jurisdiction: JurisdictionEnum = Field(..., description="Related party jurisdiction")
    amount: Optional[float] = Field(None, gt=0, description="Transaction amount")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$", description="Currency code (ISO 4217)")
    fiscal_year: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$", description="Fiscal year (e.g., 2023-24)")
    functional_profile: FunctionalProfile = Field(..., description="Functional analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": 1,
                "transaction_type": "services",
                "description": "Software development services provided to US parent",
                "related_party_name": "TechCorp USA Inc",
                "related_party_jurisdiction": "US",
                "amount": 5000000.00,
                "currency": "USD",
                "fiscal_year": "2023-24",
                "functional_profile": {
                    "functions": ["Software development", "Testing"],
                    "assets": ["Employee skills", "Infrastructure"],
                    "risks": ["Operational risk (low)"],
                    "risk_level": "low"
                }
            }
        }

class PolicyGenerationRequest(BaseModel):
    """Schema for policy generation request."""
    company_id: int = Field(..., gt=0, description="ID of the company")
    transaction_ids: List[int] = Field(..., min_items=1, description="List of transaction IDs to include")
    fiscal_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Fiscal year for the policy")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_id": 1,
                "transaction_ids": [1, 2, 3],
                "fiscal_year": "2023-24"
            }
        }

class PolicyReviewRequest(BaseModel):
    """Schema for policy review submission."""
    reviewed_by: str = Field(..., min_length=1, max_length=255, description="Reviewer name")
    review_comments: Optional[str] = Field(None, description="Review comments")
    approved: bool = Field(..., description="Whether the policy is approved")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reviewed_by": "John Doe",
                "review_comments": "Approved with minor suggestions",
                "approved": True
            }
        }

class SectionUpdateRequest(BaseModel):
    """Schema for updating a policy section."""
    content: str = Field(..., min_length=1, description="Updated section content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated executive summary text..."
            }
        }
