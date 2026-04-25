from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    credits = Column(Integer, default=100)
    total_generations = Column(Integer, default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class Generation(Base):
    __tablename__ = 'generations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(String(20))  # image, video, lipsync, cinema
    model = Column(String(100))
    prompt = Column(Text)
    input_images = Column(JSON)  # URLs or file_ids
    audio_url = Column(String(500))
    output_url = Column(String(500))
    status = Column(String(20))  # pending, processing, completed, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class ModelList(Base):
    __tablename__ = 'models'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    category = Column(String(20))  # t2i, i2i, t2v, i2v, lipsync
    endpoint = Column(String(200))
    max_images = Column(Integer, default=1)
    supports_resolution = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    credits_cost = Column(Integer, default=1)
