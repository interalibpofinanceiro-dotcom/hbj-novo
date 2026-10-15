"""Gera hinos.json a partir do stage1.json (saída do extract.py).

Regra: as PALAVRAS são as do PDF original, sem correção. O script só decide
quebras de linha/estrofe (o PDF do Canva quebra linhas pela largura da caixa).

uso: python build_hymns.py stage1.json index_titles.json ../hinos.json
"""
import json, re, sys, collections

stage1, index_path, out_path = sys.argv[1:4]
H = json.load(open(stage1, encoding='utf-8'))['hymns']
IDX = {int(k): v for k, v in json.load(open(index_path, encoding='utf-8')).items()}

# títulos ausentes no PDF (no lugar do título há só os créditos / "cc")
MISSING_TITLES = {30: 'Refúgio', 324: 'Graças dou'}

STANZA_GAP = 15.5

LABEL_RE = re.compile(
    r'((?:[A-D]\. )?(?:Transc\. e Arr\.|Tradução e Arranjo|Letra e [Mm]úsica e Arranjo|etra e Música e Arranjo|'
    r'Letram e Música|Letra e [Mm]úsica|Letra|Música|Músic|Tradução|Trad\.?|Arranjo|Arr\.|Adapt\.|Transc\.))\s*:')


def join_wrapped(parts):
    s = ''
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not s:
            s = p
        elif s.endswith('-') and not s.endswith(' -') and p[:1].isalnum():
            s += p
        else:
            s += ' ' + p
    return s


def split_hymns_with_two_credit_blocks(hymns):
    """O título do 30 e do 324 não existe no PDF: os créditos deles caem
    dentro do hino anterior. Separa pelo 2º bloco de créditos."""
    out = []
    for h in hymns:
        toms = [i for i, c in enumerate(h['cred']) if 'Tom:' in c['t']]
        if len(toms) < 2 or h['numero'] + 1 not in MISSING_TITLES:
            out.append(h)
            continue
        cut = toms[0] + 1
        second_cred = h['cred'][cut:]
        y0, p0 = second_cred[0]['y'], second_cred[0]['p']
        before = [l for l in h['body'] if (l['p'], l['y']) < (p0, y0)]
        after = [l for l in h['body'] if (l['p'], l['y']) >= (p0, y0)]
        n = h['numero'] + 1
        out.append(dict(h, cred=h['cred'][:cut], body=before))
        out.append(dict(numero=n, titulo=MISSING_TITLES[n], page=p0, cred=second_cred, body=after))
    return out


def parse_credits(cred_lines):
    text = join_wrapped([c['t'] for c in cred_lines])
    toms = re.findall(r'Tom:\s*(\S+)', text)
    text = re.sub(r'\s*Tom:\s*\S+', '', text).strip()
    tom = ' / '.join(dict.fromkeys(toms))
    # uma linha por rótulo (Letra:, Música:, Trad.: ...) — sem mudar palavras
    pieces, last = [], 0
    for mm in LABEL_RE.finditer(text):
        if mm.start() > last:
            pieces.append(text[last:mm.start()])
            last = mm.start()
    pieces.append(text[last:])
    lines = [re.sub(r'\s+', ' ', p).strip() for p in pieces if p.strip()]
    return '\n'.join(lines), tom


PARA_GAP = 12.5


def group_stanzas(body):
    """Separa estrofes pela distância vertical. No Canva, a 1ª linha de cada
    parágrafo fica com espaço maior antes E depois dela (~13-14pt)."""
    body = [l for l in body if l['t'].strip() and not set(l['t'].strip()) <= set('■▪ ')]
    stanzas = []  # dict(lines=[...], italic=bool, note=bool)
    for i, l in enumerate(body):
        t = l['t'].strip()
        prev = body[i - 1] if i else None
        nxt = body[i + 1] if i + 1 < len(body) else None
        note = l['size'] == 8.0
        new = prev is None
        if prev is not None:
            gap = l['y'] - prev['y']
            if l['p'] != prev['p']:
                # quebra de página: só é nova estrofe se a anterior terminou frase
                new = bool(re.search(r'[.!?”"]\s*$', prev['t'].strip())) or l['it'] != prev['it']
            elif gap > STANZA_GAP:
                new = True
            elif l['it'] != prev['it'] or note != stanzas[-1]['note']:
                new = True
            elif gap >= PARA_GAP and nxt is not None and nxt['p'] == l['p']                     and PARA_GAP <= nxt['y'] - l['y'] <= STANZA_GAP and len(stanzas[-1]['lines']) >= 2:
                new = True
        if new:
            stanzas.append(dict(lines=[], italic=l['it'], note=note))
        stanzas[-1]['lines'].append(t)
    return stanzas


def is_wrapped(lines):
    return any(t[:1].islower() for t in lines[1:]) or sum(1 for t in lines if len(t.split()) == 1) >= 2


def candidates(words):
    """posições (índice da palavra) onde uma nova linha pode começar"""
    c = []
    for i in range(1, len(words)):
        w = words[i].lstrip('“"\'(¡¿')
        if w[:1].isupper():
            c.append(i)
    return c


def reflow(lines, ref):
    words = join_wrapped(lines).split()
    cand = candidates(words)
    total = len(' '.join(words))
    if not ref:
        ref = [30.0]  # comprimento típico de verso no HBJ
    # a estrofe pode ter 2x/3x as linhas da referência (ex.: estrofe dupla)
    reps = max(1, round(total / sum(ref)))
    ref = ref * reps
    K = len(ref)
    if K and 1 <= K - 1 <= len(cand):
        # DP: escolhe K-1 pontos de corte minimizando diferença p/ comprimentos de referência
        pos = [0] + cand + [len(words)]
        L = lambda a, b: len(' '.join(words[pos[a]:pos[b]]))
        INF = float('inf')
        n = len(pos)
        best = {(0, 0): (0, None)}
        for k in range(1, K + 1):
            for j in range(1, n):
                if k == K and j != n - 1:
                    continue
                if k < K and j == n - 1:
                    continue
                bc, bp = INF, None
                for i in range(j):
                    if (k - 1, i) in best:
                        c = best[(k - 1, i)][0] + (L(i, j) - ref[k - 1]) ** 2
                        if c < bc:
                            bc, bp = c, i
                if bp is not None:
                    best[(k, j)] = (bc, bp)
        if (K, n - 1) in best:
            cuts, k, j = [], K, n - 1
            while k > 0:
                i = best[(k, j)][1]
                cuts.append((i, j))
                j, k = i, k - 1
            return [' '.join(words[pos[a]:pos[b]]) for a, b in reversed(cuts)]
    # sem referência: corta antes de maiúscula precedida de pontuação
    out, curw = [], []
    for i, w in enumerate(words):
        if curw and w.lstrip('“"\'(')[:1].isupper() and re.search(r'[,;:!?.”]$', curw[-1]):
            out.append(' '.join(curw))
            curw = []
        curw.append(w)
    if curw:
        out.append(' '.join(curw))
    return out


def fix_stanzas(stanzas):
    for s in stanzas:
        s['wrapped'] = not s['note'] and is_wrapped(s['lines'])
    for s in stanzas:
        if not s['wrapped']:
            continue
        sib = [x for x in stanzas if x is not s and not x['wrapped'] and not x['note'] and x['italic'] == s['italic']]
        if not sib:
            sib = [x for x in stanzas if x is not s and not x['wrapped'] and not x['note']]
        ref = None
        if sib:
            K = collections.Counter(len(x['lines']) for x in sib).most_common(1)[0][0]
            same = [x for x in sib if len(x['lines']) == K]
            ref = [sum(len(x['lines'][i]) for x in same) / len(same) for i in range(K)]
        s['lines'] = reflow(s['lines'], ref)
        same_type = sib and all(x['italic'] == s['italic'] for x in sib)
        if ref and same_type and len(s['lines']) > len(ref) and len(s['lines']) % len(ref) == 0:
            s['split_every'] = len(ref)  # caixa do Canva com várias estrofes juntas
    out = []
    for s in stanzas:
        k = s.get('split_every')
        if not k:
            out.append(s)
            continue
        for i in range(0, len(s['lines']), k):
            out.append(dict(s, lines=s['lines'][i:i + k]))
    return out


hymns = split_hymns_with_two_credit_blocks(H)
result, report = [], []
for h in hymns:
    creditos, tom = parse_credits(h['cred'])
    st = fix_stanzas(group_stanzas(h['body']))
    titulo = h['titulo']
    hino = dict(numero=h['numero'], titulo=titulo, creditos=creditos, tom=tom,
                estrofes=['\n'.join(s['lines']) for s in st if not s['note']],
                coros=[i for i, s in enumerate([s for s in st if not s['note']]) if s['italic']])
    notes = [' '.join(s['lines']) for s in st if s['note']]
    if notes:
        hino['nota'] = '\n'.join(notes)
    result.append(hino)
    if any(s['wrapped'] for s in st):
        report.append(h['numero'])

# verificação de fidelidade: mesmas palavras, mesma ordem, do PDF
for h, r in zip(hymns, result):
    src = join_wrapped([l['t'] for l in h['body'] if l['size'] != 8.0 and not set(l['t'].strip()) <= set('■▪ ')]).split()
    dst = ' '.join(r['estrofes']).split()
    assert src == dst, ('palavras divergentes no hino', r['numero'])

result.sort(key=lambda x: x['numero'])
assert [r['numero'] for r in result] == list(range(1, len(result) + 1)), 'numeração com buracos'
json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('hinos:', len(result))
print('com estrofes reajustadas (quebra de linha do Canva):', len(report))
print('sem tom:', [r['numero'] for r in result if not r['tom']])
print('sem estrofes:', [r['numero'] for r in result if not r['estrofes']])
