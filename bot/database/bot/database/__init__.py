from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, User, Generation, ModelList
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://mimi:password@postgres:5432/mimi_ai')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
    
    # Добавляем все 200+ моделей
    db = SessionLocal()
    models_data = [
        # Text-to-Image (50+)
        ("Flux Dev", "t2i", "flux-dev", 1, True, 1),
        ("Flux Pro", "t2i", "flux-pro", 1, True, 2),
        ("Midjourney v7", "t2i", "midjourney-v7", 1, True, 2),
        ("Nano Banana 2", "t2i", "nano-banana-2", 1, True, 1),
        ("Seedream 5.0", "t2i", "seedream-5.0", 1, True, 1),
        ("Ideogram v3", "t2i", "ideogram-v3", 1, True, 1),
        ("GPT-4o Image", "t2i", "gpt-4o-image", 1, True, 2),
        ("SDXL 1.0", "t2i", "sdxl-1.0", 1, True, 1),
        
        # Image-to-Image (55+)
        ("Nano Banana 2 Edit", "i2i", "nano-banana-2-edit", 14, True, 2),
        ("Flux Kontext Pro", "i2i", "flux-kontext-pro", 2, True, 2),
        ("GPT-4o Edit", "i2i", "gpt-4o-edit", 10, True, 2),
        ("Seededit v3", "i2i", "seededit-v3", 10, True, 1),
        ("Kling O1 Edit", "i2i", "kling-o1-edit", 10, True, 2),
        
        # Text-to-Video (40+)
        ("Kling v3", "t2v", "kling-v3", 1, True, 5),
        ("Sora 2", "t2v", "sora-2", 1, True, 5),
        ("Veo 3", "t2v", "veo-3", 1, True, 5),
        ("Wan 2.6", "t2v", "wan-2.6", 1, True, 4),
        ("Seedance 2.0", "t2v", "seedance-2.0", 1, True, 4),
        ("Runway Gen-3", "t2v", "runway-gen3", 1, True, 5),
        
        # Image-to-Video (60+)
        ("Kling I2V", "i2v", "kling-i2v", 1, True, 5),
        ("Veo 3 I2V", "i2v", "veo-3-i2v", 1, True, 5),
        ("Seedance 2.0 I2V", "i2v", "seedance-2.0-i2v", 9, True, 5),
        ("Midjourney I2V", "i2v", "midjourney-i2v", 1, True, 5),
        ("Wan 2.2 I2V", "i2v", "wan-2.2-i2v", 1, True, 4),
        
        # Lip Sync (9)
        ("Infinite Talk", "lipsync", "infinitetalk-image-to-video", 1, True, 3),
        ("Wan 2.2 Speech", "lipsync", "wan2.2-speech-to-video", 1, True, 3),
        ("LTX 2.3 Lipsync", "lipsync", "ltx-2.3-lipsync", 1, True, 3),
        ("LatentSync", "lipsync", "latentsync-video", 1, True, 3),
        ("Sync Lipsync", "lipsync", "sync-lipsync", 1, True, 3),
    ]
    
    for name, cat, endpoint, max_img, res, cost in models_data:
        if not db.query(ModelList).filter_by(name=name).first():
            model = ModelList(
                name=name, category=cat, endpoint=endpoint,
                max_images=max_img, supports_resolution=res,
                credits_cost=cost, is_active=True
            )
            db.add(model)
    
    db.commit()
    db.close()
