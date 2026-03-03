"""
Seed script to create test users in the database.
Usage: python seed.py
"""
from app.database import SessionLocal, engine
from app.models import Base, User
from app.auth import hash_password


def seed_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if users already exist
    admin_exists = db.query(User).filter(User.email == "admin@handwriteai.com").first()
    user_exists = db.query(User).filter(User.email == "user@handwriteai.com").first()
    
    if not admin_exists:
        admin = User(
            full_name="Admin User",
            email="admin@handwriteai.com",
            hashed_password=hash_password("admin123"),
            role="admin"
        )
        db.add(admin)
        print("✅ Created admin user: admin@handwriteai.com / password: admin123")
    else:
        print("⚠️  Admin user already exists")
    
    if not user_exists:
        user = User(
            full_name="Test User",
            email="user@handwriteai.com",
            hashed_password=hash_password("user123"),
            role="user"
        )
        db.add(user)
        print("✅ Created test user: user@handwriteai.com / password: user123")
    else:
        print("⚠️  Test user already exists")
    
    db.commit()
    db.close()
    print("\n✅ Database seeding complete!")


if __name__ == "__main__":
    seed_database()
