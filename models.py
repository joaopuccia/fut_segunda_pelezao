from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Jogador(db.Model):
    __tablename__ = 'jogadores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False, index=True)
    telefone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Partida(db.Model):
    __tablename__ = 'partidas'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Inscricao(db.Model):
    __tablename__ = 'inscricoes'
    id = db.Column(db.Integer, primary_key=True)
    partida_id = db.Column(db.Integer, db.ForeignKey('partidas.id'), nullable=False, index=True)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogadores.id'), nullable=False, index=True)
    posicao = db.Column(db.String(3), nullable=False)
    posicao_secundaria = db.Column(db.String(3))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    arrived_at = db.Column(db.DateTime, nullable=True)
    arrival_order = db.Column(db.Integer, nullable=True)
    partida = db.relationship('Partida', backref='inscricoes')
    jogador = db.relationship('Jogador', backref='inscricoes')
    __table_args__ = (db.UniqueConstraint('partida_id','jogador_id', name='uq_partida_jogador'),)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('partidas.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    idx = db.Column(db.Integer, nullable=False)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    inscricao_id = db.Column(db.Integer, db.ForeignKey('inscricoes.id'), nullable=False, index=True)
    position = db.Column(db.String(3), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('partidas.id'), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    scorer_player_id = db.Column(db.Integer, db.ForeignKey('jogadores.id'), nullable=False, index=True)
    assist_player_id = db.Column(db.Integer, db.ForeignKey('jogadores.id'), nullable=True, index=True)
    scorer_name = db.Column(db.String(200), nullable=False)
    assist_name = db.Column(db.String(200), nullable=True)
    minute = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
