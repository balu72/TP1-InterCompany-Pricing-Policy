"""Company model for storing client company information."""
from .base import db, TimestampMixin
from sqlalchemy.dialects.postgresql import JSON

class Company(db.Model, TimestampMixin):
    """Represents a company for which transfer pricing policies are generated."""
    
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    jurisdiction = db.Column(db.String(50), nullable=False)  # "India" or "US"
    tax_id = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=False)  # "manufacturer", "distributor", "service_provider"
    
    # Additional fields
    address = db.Column(db.Text)
    industry = db.Column(db.String(100))
    fiscal_year_end = db.Column(db.String(10))  # "31-Mar", "31-Dec"
    
    # Relationships
    transactions = db.relationship('Transaction', back_populates='company', cascade='all, delete-orphan')
    policies = db.relationship('Policy', back_populates='company', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'jurisdiction': self.jurisdiction,
            'tax_id': self.tax_id,
            'entity_type': self.entity_type,
            'address': self.address,
            'industry': self.industry,
            'fiscal_year_end': self.fiscal_year_end,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Company {self.name} ({self.jurisdiction})>'
