"""Policy model for storing generated transfer pricing policies."""
from .base import db, TimestampMixin
from sqlalchemy.dialects.postgresql import JSON

class Policy(db.Model, TimestampMixin):
    """Represents a generated transfer pricing policy document."""
    
    __tablename__ = 'policies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Policy metadata
    status = db.Column(db.String(20), nullable=False, default='draft')  # "draft", "generating", "review", "approved", "rejected"
    version = db.Column(db.Integer, default=1)
    fiscal_year = db.Column(db.String(10))
    
    # Generated content (stored as JSON sections)
    sections = db.Column(JSON, default=dict)  # {"executive_summary": "...", "related_parties": "...", ...}
    
    # Sections structure:
    # {
    #   "executive_summary": {"content": "...", "status": "generated", "citations": [...]},
    #   "related_parties": {"content": "...", "status": "generated", "citations": [...]},
    #   "functional_analysis": {"content": "...", "status": "generated", "citations": [...]},
    #   "comparability_analysis": {"content": "...", "status": "generating", "citations": []},
    #   "tp_method": {"content": "...", "status": "pending", "citations": []},
    #   "benchmarking": {"content": "...", "status": "pending", "citations": []},
    #   "documentation_requirements": {"content": "...", "status": "pending", "citations": []}
    # }
    
    # Review and approval
    reviewed_by = db.Column(db.String(255))
    reviewed_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(255))
    approved_at = db.Column(db.DateTime)
    review_comments = db.Column(db.Text)
    
    # Generation metadata
    generation_progress = db.Column(db.Integer, default=0)  # 0-100 percentage
    generation_log = db.Column(JSON, default=list)  # Log of generation steps
    
    # Relationships
    company = db.relationship('Company', back_populates='policies')
    
    def to_dict(self, include_sections=True):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'company_id': self.company_id,
            'status': self.status,
            'version': self.version,
            'fiscal_year': self.fiscal_year,
            'generation_progress': self.generation_progress,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'review_comments': self.review_comments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sections:
            result['sections'] = self.sections or {}
            result['generation_log'] = self.generation_log or []
        
        return result
    
    def get_section(self, section_name):
        """Get a specific section."""
        if self.sections and section_name in self.sections:
            return self.sections[section_name]
        return None
    
    def update_section(self, section_name, content, status='generated', citations=None):
        """Update a specific section."""
        if not self.sections:
            self.sections = {}
        
        self.sections[section_name] = {
            'content': content,
            'status': status,
            'citations': citations or []
        }
        db.session.commit()
    
    def __repr__(self):
        return f'<Policy {self.id} - {self.status} ({self.company.name if self.company else "No Company"})>'
