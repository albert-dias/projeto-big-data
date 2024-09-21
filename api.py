# -*- coding: utf-8 -*-
#pip install PyJWT
#pip install Flask

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime as dt

app = Flask(__name__)

app.config['SECRET_KEY'] = 'mudar_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/app_coleta'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

# TABELAS
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    senha = db.Column(db.String(200), nullable=False)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf_cnpj = db.Column(db.String(18), nullable=False, unique=False)
    coletas = db.relationship('Coleta', backref='cliente', lazy=True)

class Coleta(db.Model):
    __tablename__ = 'coletas'
    id = db.Column(db.Integer, primary_key=True)
    data_coleta = db.Column(db.Date, nullable=False)
    efetuada = db.Column(db.Boolean, default=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)

# FIM TABELAS=========================================================================

#@app.before_first_request
#def create_tables():
#    db.create_all()

@app.route('/usuarios', methods=['POST'])
def cadastrar_usuario():
    data = request.json
    nome = data.get('nome')
    email = data.get('email')
    senha = data.get('senha')

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"message": "Email já registrado."}), 400
    
    senha_hash = generate_password_hash(senha)

    novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)

    db.session.add(novo_usuario)
    db.session.commit()

    return jsonify({"message": "Usuário cadastrado com sucesso!", "usuario": {
        "id": novo_usuario.id,
        "nome": novo_usuario.nome,
        "email": novo_usuario.email
    }}), 201

def gerar_token(usuario_id):
    token = jwt.encode({
        'id': usuario_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return token

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    senha = data.get('senha')

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return jsonify({"message": "Usuário não existe"}), 401

    if not check_password_hash(usuario.senha, senha):
        return jsonify({"message": "Email ou senha incorretos."}), 401

    token = gerar_token(usuario.id)

    return jsonify({
        "message": "OK!",
        "usuario": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email
        },
        "token": token
    })

def token_required(f):
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token ausente!"}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            usuario_id = data['id']
        except:
            return jsonify({"message": "Token inválido!"}), 401
        
        return f(usuario_id, *args, **kwargs)
    return decorator


@app.route('/usuarios', methods=['GET'])
@token_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    lista_usuarios = [{"id": usuario.id, "nome": usuario.nome, "email": usuario.email} for usuario in usuarios]
    return jsonify(lista_usuarios)


@app.route('/clientes', methods=['POST'])
@token_required
def cadastrar_cliente():
    data = request.json
    nome = data.get('nome')
    cpf_cnpj = data.get('cpf_cnpj')
    
    if Cliente.query.filter_by(cpf_cnpj=cpf_cnpj).first():
        return jsonify({"message": "Cliente com esse CPF/CNPJ já existe!"}), 400
    
    novo_cliente = Cliente(nome=nome, cpf_cnpj=cpf_cnpj)
    
    db.session.add(novo_cliente)
    db.session.commit()
    
    return jsonify({"message": "Cliente cadastrado com sucesso!", "cliente": {
        "id": novo_cliente.id,
        "nome": novo_cliente.nome,
        "cpf_cnpj": novo_cliente.cpf_cnpj
    }}), 201

@app.route('/clientes', methods=['GET'])
@token_required
def listar_clientes():
    clientes = Cliente.query.all()
    lista_clientes = [{"id": cliente.id, "nome": cliente.nome, "cpf_cnpj": cliente.cpf_cnpj} for cliente in clientes]
    return jsonify(lista_clientes)


@app.route('/coletas', methods=['POST'])
@token_required
def registrar_coleta():
    data = request.json
    cliente_id = data.get('cliente_id')
    data_coleta = data.get('data_coleta')
    efetuada = data.get('efetuada', False)

    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({"message": "Cliente não encontrado"}), 404
    
    try:
        #data_coleta = datetime.strptime(data_coleta, '%Y-%m-%d').date()
        data_coleta = dt.strptime(data_coleta, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"message": "Data inválida. Use o formato YYYY-MM-DD."}), 400
    
    nova_coleta = Coleta(cliente_id=cliente_id, data_coleta=data_coleta, efetuada=efetuada)

    db.session.add(nova_coleta)
    db.session.commit()

    return jsonify({
        "message": "Coleta registrada com sucesso!",
        "coleta": {
            "id": nova_coleta.id,
            "cliente_id": nova_coleta.cliente_id,
            "data_coleta": nova_coleta.data_coleta.strftime('%Y-%m-%d'),
            "efetuada": nova_coleta.efetuada
        }
    }), 201

@app.route('/clientes/<int:cliente_id>/coletas', methods=['GET'])
@token_required
def listar_coletas_cliente(cliente_id):
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({"message": "Cliente não encontrado"}), 404
    
    coletas = Coleta.query.filter_by(cliente_id=cliente_id).all()
    lista_coletas = [
        {
            "id": coleta.id,
            "data_coleta": coleta.data_coleta.strftime('%Y-%m-%d'),
            "efetuada": coleta.efetuada
        }
        for coleta in coletas
    ]

    return jsonify({
        "cliente": {
            "id": cliente.id,
            "nome": cliente.nome,
            "cpf_cnpj": cliente.cpf_cnpj
        },
        "coletas": lista_coletas
    })

if __name__ == '__main__':
    app.run(debug=True)
