"""
Database models for ScioScribe AI Research Co-pilot.

Simple experiment model for storing experimental plans, visualizations, and data.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

# Create declarative base
Base = declarative_base()


class Experiment(Base):
    """Simple experiment model for storing plans, visualizations, and data."""
    __tablename__ = 'experiments'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Core experiment data
    experimental_plan = Column(Text, nullable=True)
    visualization_html = Column(Text, nullable=True)
    csv_data = Column(Text, nullable=True)
    
    # CSV versioning fields
    previous_csv = Column(Text, nullable=True)
    csv_version = Column(Integer, default=0)
    agent_modified_at = Column(DateTime, nullable=True)
    modification_source = Column(String, default='user')
    
    # Metadata
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Experiment(id={self.id}, title={self.title})>" 