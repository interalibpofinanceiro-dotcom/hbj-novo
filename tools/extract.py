"""Extrai os hinos do PDF do HBJ (Canva) usando posição/fonte dos spans."""
import fitz, re, json, sys

PDF = sys.argv[1]
OUT = sys.argv[2]
d = fitz.open(PDF)

TITLE_RE = re.compile(r'^(\d{1,3})\.\s+(.*\S)\s*$')

# 1) coleta de linhas visuais: (page, y, x, size, italic, text)
lines = []
for pi, page in enumerate(d):
    if pi == 0:
        continue
    items = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text']
                if not t.strip():
                    continue
                size = round(s['size'], 1)
                if s['color'] != 0 or size in (7.0, 8.0, 10.0) and not TITLE_RE.match(t.strip()):
                    # número de página, lixo ('cc'), rodapés
                    if size == 8.0 and 'Italic' in s['font']:
                        pass  # nota de rodapé (batismo) - mantida como nota
                    else:
                        continue
                items.append(dict(p=pi + 1, y=s['bbox'][1], y1=s['bbox'][3], x=s['bbox'][0], size=size,
                                  it='Italic' in s['font'], t=t))
    if any(i['size'] == 11.0 or i['size'] == 18.0 or i['size'] == 12.0 for i in items):
        break  # chegou nos índices
    items.sort(key=lambda i: (round(i['y'] / 3), i['x']))
    # funde spans na mesma linha
    merged = []
    for i in items:
        if merged and abs(merged[-1]['y'] - i['y']) < 3.5 and merged[-1]['size'] == i['size'] \
                and merged[-1]['p'] == i['p']:
            m = merged[-1]
            sep = '' if m['t'].endswith(' ') or i['t'].startswith(' ') else ' '
            m['t'] += sep + i['t']
            m['it'] = m['it'] and i['it'] if i['t'].strip() else m['it']
            m['y1'] = max(m['y1'], i['y1'])
        else:
            merged.append(dict(i))
    lines.extend(merged)
    last_page = pi + 1

# 2) agrupa por hino
hymns = []
cur = None
for ln in lines:
    t = ln['t'].strip()
    m = TITLE_RE.match(t) if ln['size'] == 10.6 else None
    if m:
        cur = dict(numero=int(m.group(1)), titulo=m.group(2), page=ln['p'], cred=[], body=[])
        hymns.append(cur)
        continue
    if cur is None:
        continue
    if ln['size'] == 7.6:
        cur['cred'].append(ln)
    else:
        cur['body'].append(ln)

json.dump(dict(last_page=last_page, hymns=hymns), open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('hinos:', len(hymns), 'ultima pagina de hinos:', last_page)
nums = [h['numero'] for h in hymns]
print('faltando:', sorted(set(range(1, max(nums) + 1)) - set(nums)))
import collections
print('duplicados:', [n for n, c in collections.Counter(nums).items() if c > 1])
print('fora de ordem:', [(a, b) for a, b in zip(nums, nums[1:]) if b != a + 1][:40])
