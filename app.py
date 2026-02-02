import os
from datetime import datetime
from functools import wraps
from collections import Counter

from flask import Flask, render_template, redirect, url_for, request, flash, Response
from models import db, Jogador, Partida, Inscricao, Team, Assignment, Goal
from forms import InscricaoForm
from logic import formar_times, DEFAULT_FORMATION
from utils import proxima_segunda

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        pwd = request.headers.get('X-Admin-Token') or request.args.get('admin')
        if pwd == ADMIN_PASSWORD:
            return f(*args, **kwargs)
        return Response('Unauthorized', 401)
    return wrapper

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, 'futseg.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.get('/')
    def index():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        locked = False
        times_view, espera, ranking = [], [], None
        if partida and partida.status == 'locked':
            locked = True
            teams = Team.query.filter_by(match_id=partida.id).order_by(Team.idx.asc()).all()
            for t in teams:
                assigns = Assignment.query.filter_by(team_id=t.id).all()
                jogadores = []
                for a in assigns:
                    insc = Inscricao.query.get(a.inscricao_id)
                    jogadores.append({'nome': insc.jogador.nome, 'pos': a.position})
                times_view.append({'nome': t.name, 'jogadores': jogadores})
        else:
            if not partida:
                partida = Partida(data=data_partida)
                db.session.add(partida)
                db.session.commit()
            ins = Inscricao.query.filter_by(partida_id=partida.id).order_by(Inscricao.created_at.asc()).all()
            data = [{
                'id': i.id, 'jogador_nome': i.jogador.nome,
                'posicao': i.posicao, 'posicao_secundaria': i.posicao_secundaria,
                'created_at': i.created_at.isoformat(), 'arrival_order': i.arrival_order
            } for i in ins]
            t, e = formar_times(data, teams_count=4, formation=DEFAULT_FORMATION)
            for idx, ti in enumerate(t, start=1):
                times_view.append({'nome': f'Time {idx}', 'jogadores': ti['jogadores']})
            espera = e
        return render_template('index.html', data=data_partida, times=times_view, espera=espera, locked=locked, ranking=ranking)

    @app.get('/inscricao')
    def inscricao_get():
        form = InscricaoForm()
        data_partida = proxima_segunda()
        return render_template('inscricao.html', form=form, data=data_partida)

    @app.post('/inscricao')
    def inscricao_post():
        form = InscricaoForm()
        if not form.validate_on_submit():
            flash('Preencha o formulário corretamente.', 'danger')
            return redirect(url_for('inscricao_get'))
        nome = form.nome.data.strip()
        pos = form.posicao.data
        pos2 = form.posicao_secundaria.data or None
        if pos2 == '': pos2 = None
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        if not partida:
            partida = Partida(data=data_partida)
            db.session.add(partida)
            db.session.commit()
        jogador = Jogador.query.filter_by(nome=nome).first()
        if not jogador:
            jogador = Jogador(nome=nome)
            db.session.add(jogador)
            db.session.commit()
        ins = Inscricao(partida_id=partida.id, jogador_id=jogador.id, posicao=pos, posicao_secundaria=pos2)
        db.session.add(ins)
        try:
            db.session.commit()
            flash(f'Inscrição confirmada para {data_partida.strftime("%d/%m/%Y")}.', 'success')
            return redirect(url_for('index'))
        except Exception:
            db.session.rollback()
            flash('Você já está inscrito nessa partida.', 'danger')
            return redirect(url_for('inscricao_get'))

    @app.get('/admin')
    @require_admin
    def admin_home():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        status = partida.status if partida else 'open'
        return render_template('admin_home.html', data=data_partida, status=status)

    @app.get('/admin/checkin')
    @require_admin
    def admin_checkin():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        inscricoes = []
        if partida:
            inscricoes = Inscricao.query.filter_by(partida_id=partida.id).order_by(Inscricao.created_at.asc()).all()
        return render_template('admin_checkin.html', data=data_partida, inscricoes=inscricoes)

    @app.route('/admin/checkin/<int:inscricao_id>/arrive', methods=['POST'])
    @require_admin
    def admin_arrive(inscricao_id):
        s = Inscricao.query.get_or_404(inscricao_id)
        max_order = db.session.query(db.func.max(Inscricao.arrival_order)).filter(Inscricao.partida_id==s.partida_id).scalar()
        next_order = (max_order or 0) + 1
        s.arrived_at = datetime.utcnow()
        s.arrival_order = next_order
        db.session.commit()
        flash(f'Check-in registrado: {s.jogador.nome} (#{next_order}).', 'success')
        return redirect(url_for('admin_checkin', admin=request.args.get('admin','')))

    @app.route('/admin/checkin/<int:inscricao_id>/undo', methods=['POST'])
    @require_admin
    def admin_arrive_undo(inscricao_id):
        s = Inscricao.query.get_or_404(inscricao_id)
        s.arrived_at = None
        s.arrival_order = None
        db.session.commit()
        flash(f'Check-in desfeito para {s.jogador.nome}.', 'success')
        return redirect(url_for('admin_checkin', admin=request.args.get('admin','')))

    @app.get('/admin/montagem')
    @require_admin
    def admin_montagem():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        times_view, espera = [], []
        if partida:
            rows = Inscricao.query.filter_by(partida_id=partida.id).order_by(Inscricao.created_at.asc()).all()
            inscritos = [{ 'id': r.id, 'jogador_nome': r.jogador.nome, 'posicao': r.posicao, 'posicao_secundaria': r.posicao_secundaria, 'created_at': r.created_at.isoformat(), 'arrival_order': r.arrival_order } for r in rows]
            times, espera = formar_times(inscritos, teams_count=4, formation=DEFAULT_FORMATION)
            for idx, ti in enumerate(times, start=1):
                times_view.append({'nome': f'Time {idx}', 'jogadores': ti['jogadores']})
        return render_template('admin_montagem.html', data=data_partida, times=times_view, espera=espera)

    @app.route('/admin/travar', methods=['POST'])
    @require_admin
    def admin_travar():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first_or_404()
        old = Team.query.filter_by(match_id=partida.id).all()
        if old:
            old_ids = [t.id for t in old]
            Assignment.query.filter(Assignment.team_id.in_(old_ids)).delete(synchronize_session=False)
            Team.query.filter_by(match_id=partida.id).delete(synchronize_session=False)
            db.session.commit()
        rows = Inscricao.query.filter_by(partida_id=partida.id).order_by(Inscricao.created_at.asc()).all()
        inscritos = [{ 'id': r.id, 'jogador_nome': r.jogador.nome, 'posicao': r.posicao, 'posicao_secundaria': r.posicao_secundaria, 'created_at': r.created_at.isoformat(), 'arrival_order': r.arrival_order } for r in rows]
        times, _ = formar_times(inscritos, teams_count=4, formation=DEFAULT_FORMATION)
        teams = []
        for idx in range(4):
            t = Team(match_id=partida.id, name=f'Time {idx+1}', idx=idx)
            db.session.add(t)
            teams.append(t)
        db.session.commit()
        nome_to_insc = { r['jogador_nome']: r['id'] for r in inscritos }
        for idx, tv in enumerate(times):
            team = teams[idx]
            for j in tv['jogadores']:
                insc_id = nome_to_insc.get(j.get('nome'))
                a = Assignment(team_id=team.id, inscricao_id=insc_id, position=j['pos'])
                db.session.add(a)
        partida.status = 'locked'
        db.session.commit()
        flash('Equipes travadas e salvas.', 'success')
        return redirect(url_for('index'))

    @app.get('/admin/placar')
    @require_admin
    def admin_placar():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        if not partida or partida.status != 'locked':
            flash('Trave as equipes antes de registrar gols.', 'danger')
            return redirect(url_for('admin_montagem', admin=request.args.get('admin','')))
        teams = Team.query.filter_by(match_id=partida.id).order_by(Team.idx.asc()).all()
        times_roster = []
        for t in teams:
            assigns = Assignment.query.filter_by(team_id=t.id).all()
            jogadores = []
            for a in assigns:
                ins = Inscricao.query.get(a.inscricao_id)
                jogadores.append({'id': ins.jogador.id, 'nome': ins.jogador.nome, 'pos': a.position})
            times_roster.append({'team': t, 'jogadores': jogadores})
        eventos = Goal.query.filter_by(match_id=partida.id).order_by(Goal.created_at.asc()).all()
        return render_template('admin_placar.html', data=data_partida, times_roster=times_roster, eventos=eventos)

    @app.route('/admin/placar/gol', methods=['POST'])
    @require_admin
    def admin_placar_gol():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first_or_404()
        team_id = int(request.form.get('team_id'))
        scorer_id = int(request.form.get('scorer_player_id'))
        assist_id = request.form.get('assist_player_id')
        assist_id = int(assist_id) if assist_id else None
        minute = request.form.get('minute')
        minute = int(minute) if minute else None
        scorer = Jogador.query.get(scorer_id)
        assist = Jogador.query.get(assist_id) if assist_id else None
        g = Goal(match_id=partida.id, team_id=team_id, scorer_player_id=scorer_id, assist_player_id=assist_id, scorer_name=scorer.nome, assist_name=assist.nome if assist else None, minute=minute)
        db.session.add(g)
        db.session.commit()
        flash('Gol/assistência registrado.', 'success')
        return redirect(url_for('admin_placar', admin=request.args.get('admin','')))

    @app.route('/admin/placar/gol/<int:goal_id>/delete', methods=['POST'])
    @require_admin
    def admin_placar_del(goal_id):
        g = Goal.query.get_or_404(goal_id)
        db.session.delete(g)
        db.session.commit()
        flash('Evento removido.', 'success')
        return redirect(url_for('admin_placar', admin=request.args.get('admin','')))

    @app.get('/placar')
    def placar_publico():
        data_partida = proxima_segunda()
        partida = Partida.query.filter_by(data=data_partida).first()
        if not partida or partida.status != 'locked':
            flash('Placar disponível após travar as equipes.', 'danger')
            return redirect(url_for('index'))
        gols = Goal.query.filter_by(match_id=partida.id).all()
        top_scorers = Counter([g.scorer_name for g in gols]).most_common()
        top_assists = Counter([g.assist_name for g in gols if g.assist_name]).most_common()
        teams = Team.query.filter_by(match_id=partida.id).order_by(Team.idx.asc()).all()
        times_view = []
        for t in teams:
            assigns = Assignment.query.filter_by(team_id=t.id).all()
            jogadores = []
            for a in assigns:
                insc = Inscricao.query.get(a.inscricao_id)
                jogadores.append({'nome': insc.jogador.nome, 'pos': a.position})
            times_view.append({'nome': t.name, 'jogadores': jogadores})
        return render_template('index.html', data=data_partida, times=times_view, espera=[], locked=True, ranking={'scorers': top_scorers, 'assists': top_assists})

    @app.get('/estatisticas')
    def estatisticas_geral():
        gols = Goal.query.all()
        scorers = Counter([g.scorer_name for g in gols]).most_common()
        assists = Counter([g.assist_name for g in gols if g.assist_name]).most_common()
        return render_template('stats.html', scorers=scorers, assists=assists)

    @app.get('/estatisticas/<nome>')
    def estatisticas_por_nome(nome):
        nome_norm = nome.strip().lower()
        eventos = Goal.query.all()
        jogos = []
        for g in eventos:
            if (g.scorer_name and g.scorer_name.lower() == nome_norm) or (g.assist_name and g.assist_name.lower() == nome_norm):
                jogos.append(g)
        return render_template('stats_player.html', nome=nome, eventos=jogos)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
