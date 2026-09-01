"""The research-note generator: content and sanity of the HTML."""

import os

import pytest

from v02_draft import run
from v02_draft.data import load_snapshot
from v02_draft.note import build_note, build_index, fmt_px, pct, heat, write_notes

SNAPS = os.path.join(os.path.dirname(__file__), '..', 'snapshots')


def _res(symbol, fixture):
    path = os.path.join(SNAPS, fixture)
    if not os.path.exists(path):
        pytest.skip('demo snapshot not present')
    res = run.assess(symbol, load_snapshot(path))
    from v02_draft import valuation as V
    res.setdefault('bear_growth', V.clamp(res.get('hist_growth', 0.0), -0.02, 0.02))
    return res


def test_note_contains_every_section():
    html = build_note(_res('T', 'T.json'))
    for fragment in (
        'AT&T', 'rating', 'implied FCF growth', 'break-even decline',
        'Consensus (median)', 'Risk panel', 'Piotroski F-Score', 'Altman Z',
        'Sensitivity', 'Thesis on file', 'Verdict trace', 'CAUTIOUS BUY below',
        'Data quality', 'DEMO DATA', 'Not financial advice',
    ):
        assert fragment in html, f'missing section: {fragment}'
    # no un-rendered python braces leaking into the document
    assert "{'" not in html and "'}" not in html


def test_note_wrong_tool():
    b = load_snapshot(os.path.join(SNAPS, 'T.json'))
    b['industry'] = 'Insurance - Life'
    res = run.assess('T', b)
    html = build_note(res)
    assert 'WRONG TOOL' in html and 'refuses to value' in html


def test_index_links_notes():
    idx = build_index([('T', _res('T', 'T.json')),
                       ('IMB.L', _res('IMB.L', 'IMB_L.json'))])
    assert 'T_note.html' in idx and 'IMB_L_note.html' in idx
    assert 'WATCH' in idx and 'PASS' in idx


def test_formatters():
    assert fmt_px(2511.0, 'GBp') == '2,511p'
    assert fmt_px(25.67, 'USD') == '$25.67'
    assert fmt_px(None, 'USD') == 'n/a'
    assert pct(-0.079) == '-7.9%'
    assert pct(None) == 'n/a'
    assert heat(85) == 'good' and heat(55) == 'ok'
    assert heat(40) == 'warn' and heat(10) == 'bad' and heat(None) == 'grey'


def test_write_notes_end_to_end(tmp_path):
    results = write_notes(['T', 'IMB.L'], live=False, outdir=str(tmp_path))
    assert len(results) == 2
    for f in ('T_note.html', 'IMB_L_note.html', 'index.html'):
        assert (tmp_path / f).exists()
        assert (tmp_path / f).stat().st_size > 4000
