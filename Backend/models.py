from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    mobile = db.Column(db.String(15), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    verification_code = db.Column(db.String(6), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    animals = db.relationship('Animal', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'mobile': self.mobile,
            'name': self.name,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }


class Animal(db.Model):
    __tablename__ = 'animals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    animal_type = db.Column(db.String(50), nullable=False)
    photo_path = db.Column(db.String(200))
    inseminated_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date)
    calf_details = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    injections = db.relationship('Injection', backref='animal', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'animal_type': self.animal_type,
            'photo_path': self.photo_path,
            'inseminated_date': self.inseminated_date.isoformat() if self.inseminated_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'calf_details': self.calf_details,
            'notes': self.notes,
            'injections': [inj.to_dict() for inj in self.injections],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class Injection(db.Model):
    __tablename__ = 'injections'
    
    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'details': self.details
        }