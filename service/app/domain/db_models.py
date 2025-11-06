# service/app/domain/db_models.py
from sqlalchemy import Column, String, Integer, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from typing import Dict, List, Optional

Base = declarative_base()


class PackageModel(Base):
    __tablename__ = "packages"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    card_text = Column(Text, nullable=True)
    meta = Column(JSON, nullable=False, default=dict)
    parents = Column(JSON, nullable=False, default=list)
    sensitive = Column(Boolean, nullable=False, default=False)
    pre_download_hook = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    scores = Column(JSON, nullable=False, default=dict)
    blob_key_full = Column(String, nullable=True)
    blob_key_weights = Column(String, nullable=True)
    blob_key_datasets = Column(String, nullable=True)

    def to_domain(self):
        """Convert database model to domain ModelPackage"""
        from .models import ModelPackage
        return ModelPackage(
            id=self.id,
            name=self.name,
            version=self.version,
            card_text=self.card_text,
            meta=self.meta or {},
            parents=self.parents or [],
            sensitive=self.sensitive,
            pre_download_hook=self.pre_download_hook,
            size_bytes=self.size_bytes,
            scores=self.scores or {},
            blob_key_full=self.blob_key_full,
            blob_key_weights=self.blob_key_weights,
            blob_key_datasets=self.blob_key_datasets,
        )


class UserModel(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    hashed = Column(String, nullable=False)
    role = Column(String, nullable=False)
    rev = Column(Integer, nullable=False, default=0)

