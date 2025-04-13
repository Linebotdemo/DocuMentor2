from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ----------------------
# Company モデル
# ----------------------
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    users = db.relationship('User', backref='company', lazy=True)
    videos = db.relationship('Video', backref='company', lazy=True)

# ----------------------
# User モデル
# ----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='user')
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    videos = db.relationship('Video', backref='user', lazy=True)

# ----------------------
# Video モデル
# ----------------------
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    cloudinary_url = db.Column(db.String(500))
    whisper_text = db.Column(db.Text)
    summary_text = db.Column(db.Text)
    ocr_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generation_mode = db.Column(db.String(20), default="manual")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))

    quiz = db.relationship('Quiz', backref='video', uselist=False)

# ----------------------
# Quiz モデル
# ----------------------
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    title = db.Column(db.String(255))
    auto_quiz_text = db.Column(db.Text)
