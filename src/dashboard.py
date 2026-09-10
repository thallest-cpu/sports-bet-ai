import html
import json
from datetime import timedelta
import streamlit as st
from src.audit import match_state, parse_time, utcnow
from src.settings import licensed_photo
from src.prediction_service import open_ledger, reconcile
from src.sports_data_api import fixtures_on_date, now_local, player_leaders


def esc(value):
    return html.escape(str(value if value is not None else '—'), quote=True)


def theme():
    st.markdown('''<style>
    .betai-slides {display:flex; gap:16px; overflow-x:auto; scroll-snap-type:x mandatory; padding:8px 2px 22px;}
    .betai-slide {flex:0 0 min(360px,88vw); scroll-snap-align:start; padding:24px; border:1px solid #29415a;
      border-radius:22px; background:linear-gradient(135deg,#10283b,#101923); color:#f2f8ff; box-sizing:border-box;}
    .betai-slide h3 {font-size:21px; color:#f2f8ff; margin:16px 0; line-height:1.4;}
    .betai-slide small {color:#b2c5d7;} .betai-slide strong {color:#61e3bb; font-size:24px;}
    .betai-slide img {width:72px;height:72px;object-fit:contain;border-radius:50%;background:#eaf0f5;}
    .betai-tag {font-size:12px;color:#ffc275;letter-spacing:.04em;}
    .betai-probs {display:flex;justify-content:space-between;gap:12px;margin:20px 0;}
    .betai-probs div {display:flex;flex-direction:column;}
    [role="radiogroup"] {flex-wrap:wrap!important;gap:8px!important;}
    @media(max-width:640px){.block-container{padding:1.2rem 1rem 3rem!important;} .betai-slide{flex-basis:85vw;}
    h1{font-size:1.8rem!important;} [data-testid="stMetricValue"]{font-size:1.4rem;}}
    @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;}}
    </style>''', unsafe_allow_html=True)


def slides(cards, label):
    if cards:
        st.caption('Deslize para o lado ou use as setas do teclado com o carrossel em foco.')
        st.markdown(f'<section class="betai-slides" tabindex="0" aria-label="{esc(label)}">' + ''.join(cards) + '</section>', unsafe_allow_html=True)


def match_slides(matches):
    cards = []
    for match in matches:
        teams = match.get('teams') or {}
        goals = match.get('goals') or {}
        fx = match.get('fixture') or {}
        score = f"{goals.get('home') if goals.get('home') is not None else '—'} × {goals.get('away') if goals.get('away') is not None else '—'}"
        cards.append(f'<article class="betai-slide"><span class="betai-tag">{esc(match_state(match))}</span><h3>{esc(teams.get("home",{}).get("name"))}<br>{esc(teams.get("away",{}).get("name"))}</h3><strong>{esc(score)}</strong><p><small>{esc(fx.get("date"))}<br>Fonte: {esc(fx.get("source") or "API-Football")}</small></p></article>')
    slides(cards, 'Placares e resultados')


@st.cache_resource(ttl=60)
def ledger_resource():
    try:
        return open_ledger(), None
    except Exception:
        return None, 'Não foi possível conectar ao histórico. Nenhuma gravação foi confirmada.'


@st.cache_data(ttl=300, show_spinner=False)
def sync_history(league):
    ledger, error = ledger_resource()
    if ledger:
        try:
            reconcile(ledger, league)
        except Exception:
            return 'A apuração automática está temporariamente indisponível.'
    return error


def history(league):
    ledger, error = ledger_resource()
    if not ledger:
        st.info(error or 'Histórico auditável aguardando conexão com banco persistente. Nenhuma taxa de acerto disponível.')
        return
    warning = sync_history(league)
    if warning:
        st.warning(warning)
    try:
        predictions = ledger.predictions(league)
        all_settlements = ledger.settlements()
    except Exception:
        st.warning('Histórico indisponível. Não foi possível confirmar os registros.')
        return
    latest = {s['prediction_id']: s for s in all_settlements}
    evaluated = [latest[p['id']] for p in predictions if p['id'] in latest and latest[p['id']]['verdict'] in {'Acerto', 'Erro'}]
    hits = sum(s['verdict'] == 'Acerto' for s in evaluated)
    cols = st.columns(3)
    cols[0].metric('Previsões registradas', len(predictions))
    cols[1].metric('Apuradas', len(evaluated))
    cols[2].metric('Acerto observado', f'{hits/len(evaluated):.1%}' if evaluated else 'Sem amostra')
    st.caption('Acerto = seleção 1X2 mais provável acertou em 90 minutos + acréscimos. Denominador: previsões apuradas; anuladas e pendentes excluídas. Não é previsão de desempenho futuro.')
    cards = []
    for prediction in predictions[:50]:
        match = prediction['fixture']; teams = match['teams']; probs = prediction['probabilities']
        result = latest.get(prediction['id'])
        status = result['verdict'] if result else ('Aguardando resultado' if parse_time(match['fixture']['date']) <= utcnow() else 'Pré-jogo registrado')
        percentages = ''.join(f'<div><small>{label}</small><strong>{esc(probs[key])}%</strong></div>' for key,label in [('home','1 · Casa'),('draw','X · Empate'),('away','2 · Fora')])
        cards.append(f'<article class="betai-slide"><span class="betai-tag">{esc(status)}</span><h3>{esc(teams["home"]["name"])} × {esc(teams["away"]["name"])}</h3><div class="betai-probs">{percentages}</div><small>Registrada: {esc(prediction["created_at"])}<br>Modelo: {esc(prediction["model"])}<br>ID: {esc(prediction["id"][:12])}</small></article>')
    slides(cards, 'Previsões registradas e acertos apurados')
    ids = {p['id'] for p in predictions}
    st.download_button('Baixar histórico e evidências (JSON)', json.dumps({'predictions':predictions,'settlements':[s for s in all_settlements if s['prediction_id'] in ids]}, ensure_ascii=False, indent=2), file_name='betai-historico.json', mime='application/json')


def yesterday(league):
    day = now_local().date() - timedelta(days=1)
    st.header('Ontem / Resultados')
    st.caption(f'{day:%d/%m/%Y} · dia civil de Brasília. Adiamentos não são tratados como jogos encerrados.')
    matches, ok = fixtures_on_date(league, day)
    if not matches:
        (st.info if ok else st.warning)('Consulta concluída: nenhum jogo nesta data.' if ok else 'Não foi possível confirmar os jogos de ontem. Fonte indisponível.')
    match_slides(matches)
    st.subheader('Histórico de previsões')
    history(league)


def leaders(league, season):
    st.subheader('Destaques da temporada')
    metric = st.radio('Ranking', ['Artilheiros', 'Assistências'], horizontal=True)
    rows, ok, at = player_leaders(league, season, 'goals' if metric == 'Artilheiros' else 'assists')
    st.caption(f'Temporada {season} · API-Football · consulta: {at or "não confirmada"}. Dados sujeitos à atualização do provedor; ausência não equivale a zero.')
    if not rows:
        (st.info if ok else st.warning)('Ranking não fornecido para esta temporada.' if ok else 'Ranking indisponível nesta fonte/plano. Não exibimos dados de temporadas anteriores.')
        return
    cards = []
    for i, row in enumerate(rows[:20], 1):
        photo = licensed_photo(row['player'].get('photo'), row['source'])
        picture = f'<img src="{esc(photo)}" alt="{esc(row["player"].get("name"))}">' if photo else '<span aria-label="Foto não licenciada ou indisponível">◉</span>'
        cards.append(f'<article class="betai-slide"><span class="betai-tag">#{i} · {esc(metric)}</span><p>{picture}</p><h3>{esc(row["player"].get("name"))}</h3><small>{esc(row["team"])}</small><p><strong>{esc(row["goals"])}</strong> gols · <strong>{esc(row["assists"])}</strong> assistências</p></article>')
    slides(cards, 'Ranking de jogadores')
    st.caption('Fotos aparecem somente quando recebidas da API e a licença de publicação estiver confirmada na configuração.')
