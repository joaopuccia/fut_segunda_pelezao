from typing import List, Dict, Tuple, Optional
from datetime import datetime

Pos = str
Formation = Dict[Pos, int]

DEFAULT_FORMATION: Formation = {
    'GOL': 1, 'ZAG': 2, 'LAT': 2, 'VOL': 2, 'MEI': 2, 'ATA': 2,
}

def _parse_iso(dt):
    if isinstance(dt, datetime):
        return dt
    return datetime.fromisoformat(str(dt).replace('Z',''))

def _sort_key(s: Dict):
    ao = s.get('arrival_order')
    ao_key = ao if (ao is not None) else 10**9
    ca = _parse_iso(s['created_at'])
    return (ao_key, ca)

def formar_times(inscricoes: List[Dict], teams_count: int = 4, formation: Formation = DEFAULT_FORMATION) -> Tuple[List[Dict], List[Dict]]:
    times = [{ 'slots': formation.copy(), 'jogadores': [] } for _ in range(teams_count)]
    ordered = sorted(inscricoes, key=_sort_key)
    espera: List[Dict] = []

    def tentar_intervalo(pos: Pos, start_idx: int, end_idx: int) -> int:
        for idx in range(start_idx, min(end_idx, teams_count)):
            if times[idx]['slots'].get(pos, 0) > 0:
                times[idx]['slots'][pos] -= 1
                return idx
        return -1

    p2 = min(2, teams_count)

    for s in ordered:
        prim = s['posicao']
        sec: Optional[Pos] = s.get('posicao_secundaria') or None

        idx = tentar_intervalo(prim, 0, p2)
        if idx != -1:
            times[idx]['jogadores'].append({ 'nome': s['jogador_nome'], 'pos': prim })
            continue
        if sec:
            idx = tentar_intervalo(sec, 0, p2)
            if idx != -1:
                times[idx]['jogadores'].append({ 'nome': s['jogador_nome'], 'pos': sec })
                continue
        if teams_count > 2:
            idx = tentar_intervalo(prim, 2, teams_count)
            if idx != -1:
                times[idx]['jogadores'].append({ 'nome': s['jogador_nome'], 'pos': prim })
                continue
        if sec and teams_count > 2:
            idx = tentar_intervalo(sec, 2, teams_count)
            if idx != -1:
                times[idx]['jogadores'].append({ 'nome': s['jogador_nome'], 'pos': sec })
                continue
        espera.append({ 'nome': s['jogador_nome'], 'pos': prim })

    return times, espera
