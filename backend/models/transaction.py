"""Transaction model for storing related party transactions."""
from .base import db, TimestampMixin
from sqlalchemy.dialects.postgresql import JSON

class Transaction(db.Model, TimestampMixin):
    """Represents a related party transaction."""
    
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # "services", "goods", "loans", "IP", "guarantees"
    description = db.Column(db.Text, nullable=False)
    related_party_name = db.Column(db.String(255), nullable=False)
    related_party_jurisdiction = db.Column(db.String(50), nullable=False)
    
    # Financial details
    amount = db.Column(db.Numeric(15, 2))
    currency = db.Column(db.String(3), default='USD')
    fiscal_year = db.Column(db.String(10))  # "2023-24"
    
    # Functional analysis (stored as JSON)
    functions = db.Column(JSON)  # List of functions performed
    assets = db.Column(JSON)  # List of assets used
    risks = db.Column(JSON)  # List of risks assumed
    risk_level = db.Column(db.String(20))  # "low", "medium", "high"
    
    # Relationships
    company = db.relationship('Company', back_populates='transactions')
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'transaction_type': self.transaction_type,
            'description': self.description,
            'related_party_name': self.related_party_name,
            'related_party_jurisdiction': self.related_party_jurisdiction,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'fiscal_year': self.fiscal_year,
            'functions': self.functions,
            'assets': self.assets,
            'risks': self.risks,
            'risk_level': self.risk_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} - {self.related_party_name}>'
