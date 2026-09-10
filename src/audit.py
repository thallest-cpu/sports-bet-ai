"""Append-only prediction and settlement ledger. No implicit local storage in production."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

MODEL_VERSION = 'poisson-season-v1'
OUTCOMES = ('home', 'draw', 'away')


def utcnow():
    return datetime.now(timezone.utc)


def parse_time(value):
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (ValueError, TypeError):
        return None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def fixture_key(match):
    fx = match.get('fixture') or {}
    source = fx.get('source') or 'API-Football'
    if not fx.get('id'):
        raise ValueError('Partida sem identificador')
    return f"{source}:{fx['id']}"


def match_state(match, now=None):
    fx = match.get('fixture') or {}
    status = (fx.get('status') or {}).get('short')
    if status in {'FT', 'AET', 'PEN'}:
        return 'Encerrado Â· previsÃ£o expirada'
    if status in {'PST', 'CANC', 'ABD', 'SUSP', 'AWD', 'WO'}:
        return {'PST': 'Adiado', 'CANC': 'Cancelado', 'ABD': 'Abandonado', 'SUSP': 'Suspenso'}.get(status, 'Resultado administrativo')
    if status in {'LIVE', '1H', 'HT', '2H', 'ET', 'BT', 'P'}:
        return 'Ao vivo Â· previsÃ£o expirada'
    start = parse_time(fx.get('date'))
    if start and start <= (now or utcnow()):
        return 'Expirado Â· resultado nÃ£o confirmado'
    return 'Agendado' if start else 'HorÃ¡rio nÃ£o confirmado'


def regulation_result(match):
    fx = match.get('fixture') or {}
    status = (fx.get('status') or {}).get('short')
    if status not in {'FT', 'AET', 'PEN'}:
        return None
    score = (match.get('score') or {}).get('fulltime')
    if not score and status == 'FT':
        score = match.get('goals')
    if not isinstance(score, dict):
        return None
    h, a = score.get('home'), score.get('away')
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in (h, a)):
        return None
    return 'home' if h > a else 'away' if a > h else 'draw'


class Ledger:
    """PostgreSQL in production; explicit SQLite path only for tests/local use.

    Predictions are immutable, one per source fixture/model. Result corrections
    append revisions; all previous evidence remains available in the export.
    """
    def __init__(self, url):
        if not url:
            raise ValueError('Banco persistente nÃ£o configurado')
        self.url = url
        self.sqlite = url.startswith('sqlite:///')
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS predictions (id TEXT PRIMARY KEY, fixture_key TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL, kickoff TEXT NOT NULL, league INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, UNIQUE(fixture_key, model))')
            db.execute('CREATE TABLE IF NOT EXISTS settlements (id TEXT PRIMARY KEY, prediction_id TEXT NOT NULL REFERENCES predictions(id), observed_at TEXT NOT NULL, payload TEXT NOT NULL)')

    @contextmanager
    def connection(self):
        if self.sqlite:
            db = sqlite3.connect(self.url[len('sqlite:///'):], timeout=20)
        else:
            import psycopg
            db = psycopg.connect(self.url, connect_timeout=8)
        try:
            with db:
                yield db
        finally:
            db.close()

    def sql(self, statement):
        return statement if self.sqlite else statement.replace('?', '%s')

    def record(self, match, probabilities, evidence, now=None):
        now = now or utcnow()
        fx = match.get('fixture') or {}
        start = parse_time(fx.get('date'))
        if not start or start <= now or (fx.get('status') or {}).get('short') != 'NS':
            return False
        if (fx.get('source') or 'API-Football') != 'API-Football':
            return False
        vals = [probabilities.get(k) for k in OUTCOMES]
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 100 for v in vals) or abs(sum(vals) - 100) > .2:
            raise ValueError('Probabilidades invÃ¡lidas')
        observed = parse_time(evidence.get('observed_at'))
        if not observed or observed > now or observed >= start or (now - observed).total_seconds() > 6 * 3600:
            raise ValueError('EvidÃªncia ausente ou antiga')
        key = fixture_key(match)
        identity = hashlib.sha256(f'{key}|{MODEL_VERSION}'.encode()).hexdigest()
        payload = canonical({'fixture': match, 'probabilities': probabilities, 'evidence': evidence,
                             'selection': OUTCOMES[vals.index(max(vals))], 'model': MODEL_VERSION,
                             'market': '1X2 Â· 90 minutos + acrÃ©scimos', 'created_at': now.isoformat()})
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.connection() as db:
            # Database clock prevents a stale client clock admitting a late prediction.
            if not self.sqlite:
                if db.execute('SELECT clock_timestamp()').fetchone()[0] >= start:
                    return False
            cur = db.execute(self.sql('INSERT INTO predictions VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING'),
                             (identity, key, MODEL_VERSION, now.isoformat(), start.isoformat(), int(match['league']['id']), payload, digest))
            return cur.rowcount == 1

    def predictions(self, league=None):
        with self.connection() as db:
            rows = db.execute(self.sql('SELECT id, payload, digest FROM predictions' + (' WHERE league = ?' if league is not None else '') + ' ORDER BY created_at DESC'), (league,) if league is not None else ()).fetchall()
        return [dict(id=r[0], **json.loads(r[1]), sha256=r[2]) for r in rows]

    def settle(self, match, now=None):
        now = now or utcnow()
        start = parse_time((match.get('fixture') or {}).get('date'))
        if not start or start > now:
            return 0
        result = regulation_result(match)
        status = ((match.get('fixture') or {}).get('status') or {}).get('short')
        void = status in {'CANC', 'ABD', 'AWD', 'WO'}
        if not result and not void:
            return 0
        with self.connection() as db:
            if not self.sqlite:
                db.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (fixture_key(match),))
            else:
                db.execute('BEGIN IMMEDIATE')
            rows = db.execute(self.sql('SELECT id, payload FROM predictions WHERE fixture_key = ?'), (fixture_key(match),)).fetchall()
            count = 0
            for pid, raw in rows:
                prediction = json.loads(raw)
                if parse_time(prediction['created_at']) >= start:
                    continue
                verdict = 'Anulada' if void else 'Acerto' if prediction['selection'] == result else 'Erro'
                evidence = {'result': result, 'verdict': verdict, 'fixture': match}
                payload = canonical(evidence)
                # Ignore changing retrieval timestamps when determining result revisions.
                stable = canonical({'status': status, 'result': result, 'score': match.get('score'), 'goals': match.get('goals')})
                previous = db.execute(self.sql('SELECT id, payload FROM settlements WHERE prediction_id = ? ORDER BY observed_at DESC LIMIT 1'), (pid,)).fetchone()
                if previous:
                    old = json.loads(previous[1])['fixture']
                    old_stable = canonical({'status': old['fixture']['status']['short'], 'result': regulation_result(old), 'score': old.get('score'), 'goals': old.get('goals')})
                    if old_stable == stable:
                        continue
                revision = hashlib.sha256((pid + stable + (previous[0] if previous else '')).encode()).hexdigest()
                cur = db.execute(self.sql('INSERT INTO settlements VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING'), (revision, pid, now.isoformat(), payload))
                count += cur.rowcount
            return count

    def settlements(self):
        with self.connection() as db:
            rows = db.execute('SELECT id, prediction_id, observed_at, payload FROM settlements ORDER BY observed_at').fetchall()
        return [dict(id=r[0], prediction_id=r[1], observed_at=r[2], **json.loads(r[3])) for r in rows]
