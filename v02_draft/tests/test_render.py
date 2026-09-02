"""Thesis templating: {tokens} fill with the current run's live values."""

import os

import pytest

from v02_draft import run
from v02_draft.data import load_snapshot
from v02_draft.render import render, unrendered_tokens, variables

SNAPS = os.path.join(os.path.dirname(__file__), '..', 'snapshots')


@pytest.fixture(scope='module')
def imb():
    path = os.path.join(SNAPS, 'IMB_L.json')
    if not os.path.exists(path):
        pytest.skip('demo snapshot not present')
    return run.assess('IMB.L', load_snapshot(path))


DOCUMENTED = ['symbol', 'name', 'verdict', 'weight', 'price', 'fair', 'mos',
              'r', 'ig', 'ir', 'be', 'epv', 'bear_dcf', 'graham', 'mult',
              'bull_dcf', 'coverage', 'nd_ebitda', 'fscore', 'altman', 'risk']


def test_every_documented_token_resolves(imb):
    vals = variables(imb)
    for t in DOCUMENTED:
        assert t in vals and vals[t] not in ('', None), f'token {t} missing'
    assert vals['symbol'] == 'IMB.L'
    assert vals['price'] == '2,511p'
    assert vals['verdict'] == 'WATCH'
    assert vals['fscore'] == '9/9'   # hand-checked: all 9 criteria fire on this fixture


def test_render_fills_tokens(imb):
    text = ('At {price} the market implies {ig}/yr FCF growth; my fair value '
            'is {fair} (MoS {mos}), verdict {verdict}.')
    out = render(text, imb)
    assert '{' not in out and '}' not in out
    assert '2,511p' in out and 'WATCH' in out and '/yr' in out


def test_unknown_token_stays_literal(imb):
    out = render('price is {price} but {totally_made_up} stays', imb)
    assert '{totally_made_up}' in out and '2,511p' in out


def test_escaped_braces_survive(imb):
    out = render('literal {{braces}} and {price}', imb)
    assert '{{' not in out and '{braces}' in out and '2,511p' in out


def test_unrendered_tokens_flags_typos(imb):
    text = 'a {price} and a {typo_tokn}'
    assert unrendered_tokens(text, imb) == ['typo_tokn']
    assert unrendered_tokens('clean {price} {ig}', imb) == []


def test_note_renders_templated_thesis(tmp_path, imb):
    # a thesis with tokens goes in, live figures come out in the note
    imb['inputs'] = dict(imb['inputs'])
    imb['inputs']['thesis'] = ('WATCH. At {price} the market prices {ig}/yr '
                               'decline; break-even {be}. [Signed 2 Sep 2026]')
    from v02_draft import valuation as V
    imb.setdefault('bear_growth', V.clamp(imb.get('hist_growth', 0.0), -0.02, 0.02))
    from v02_draft.note import build_note
    html = build_note(imb)
    assert '2,511p' in html and '/yr' in html
    assert '{price}' not in html          # token actually replaced
    assert 'auto-refresh' in html         # the caption is shown
