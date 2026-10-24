"""Read-only structural audit of Spokane historical season aggregates."""
from pathlib import Path
import csv
import json
from collections import Counter

root = Path(__file__).resolve().parent
config = json.loads((root / 'league_config.json').read_text(encoding='utf-8-sig'))
slots = config.get('playoff_slots_by_year', {})
with (root / 'manager_mapping.csv').open(encoding='utf-8-sig', newline='') as f:
    mappings = list(csv.DictReader(f))
lookup = {(int(r['season']), str(r['team_id'])): r['manager_id'] for r in mappings}
assert len(lookup) == len(mappings), 'Duplicate team mappings'
with (root / 'yahoo_championships.csv').open(encoding='utf-8-sig', newline='') as f:
    champs = list(csv.DictReader(f))
verified = [r for r in champs if r['verification_status'].upper().startswith('VERIFIED') and 2003 <= int(r['season']) <= 2025]
assert len(verified) == 23, f'Expected 23 verified finals, got {len(verified)}'
assert len({int(r['season']) for r in verified}) == 23, 'Duplicate/missing championship season'
matchups = 0
playoffs = 0
for year in range(2003, 2026):
    file = root / 'raw_history' / str(year) / f'{year}_games.csv'
    with file.open(encoding='utf-8-sig', newline='') as f:
        games = list(csv.DictReader(f))
    weeks = 14 if year in (2003, 2004) or year >= 2021 else 13
    expected_teams = 8 if year <= 2011 else 10
    counts = Counter()
    pairs = set()
    regular = [r for r in games if int(r['week']) <= weeks]
    for r in regular:
        a, b = str(r['team1_id']), str(r['team2_id'])
        assert a != b and (year, a) in lookup and (year, b) in lookup, f'{year}: invalid mapping'
        key = (int(r['week']), *sorted((a,b)))
        assert key not in pairs, f'{year}: duplicate matchup {key}'
        pairs.add(key)
        counts[a] += 1
        counts[b] += 1
        for field in ('team1_score','team2_score'):
            assert r[field] != '' and float(r[field]) >= 0, f'{year}: invalid score'
    assert len(counts) == expected_teams, f'{year}: expected {expected_teams} teams, got {len(counts)}'
    assert all(v == weeks for v in counts.values()), f'{year}: incomplete schedule: {counts}'
    assert len(regular) == expected_teams * weeks // 2, f'{year}: incorrect game count'
    n = int(slots.get(str(year), 6))
    assert 2 <= n <= expected_teams, f'{year}: invalid playoff slot count'
    playoffs += n
    matchups += len(regular)
    print(f'{year}: PASS | teams={expected_teams} | games={len(regular)} | playoff spots={n}')
assert matchups == 1411, f'Unexpected regular-season matchup total: {matchups}'
assert playoffs == 142, f'Expected 142 playoff slots, got {playoffs}'
print(f'\nPASS: 23 complete seasons, {matchups} regular-season games, {playoffs} configured playoff slots, {len(verified)} verified finals.')
print('CAVEAT: 2003-2004 Week 17 finals are documented in championships CSV but absent from season game aggregates.')
print('CAVEAT: playoff slots are based on configured regular-season rankings, not independent bracket verification.')
