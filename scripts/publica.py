"""Publica o vídeo v2 de Claude Mods em inematds/claude-mods-video.
Release video-v2.0.0 (MP4 + SRT) + Pages: videos/index.html com player, capítulos e legendas VTT.
Idempotente: sobe só o que mudou de tamanho; commit só se houver diff. Adaptado de codex-claude-video/publica.py."""
import html, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

OUT = Path.home() / 'projetos/output/claude-mods-video'
REPO = Path.home() / 'projetos/claude-mods-video'
GH = 'inematds/claude-mods-video'
TAG = 'video-v2.0.0'
BASE = f'https://github.com/{GH}/releases/download/{TAG}/'
PAGES = 'https://inematds.github.io/claude-mods-video/'
FONTE = 'https://www.youtube.com/watch?v=LDn7rQKIFro'
V2 = OUT / 'v2'


def sh(*a, **kw):
    return subprocess.run(a, check=True, text=True, capture_output=True, **kw).stdout


def dur(p):
    return float(sh('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)))


def main():
    rec = json.loads((V2 / 'verification/assembled-pt.json').read_text())
    full = Path(rec['file'])
    assert full.stat().st_size == rec['bytes'] and (V2 / 'verification/decode-full-pt.log').read_text() == ''
    for b in rec['blocks']:
        assert json.loads((V2 / f'final/{b}/alignment.json').read_text())['ratio'] > .90, b
    scenes = json.loads((V2 / 'docs/lesson-pt.json').read_text())
    assert len(rec['chapters']) == len(scenes)
    v = dict(id='completo', file=full, srt=full.with_suffix('.srt'), name='claude-mods-completo-16x9',
             chapters=[(int(c['time']), scenes[c['scene'] - 1]['title']) for c in rec['chapters']])
    v['duration'] = dur(full)
    d = f"{int(v['duration'] // 60)}min{int(v['duration'] % 60):02d}s"
    stage = OUT / 'release'; stage.mkdir(exist_ok=True)
    assets = []
    for src, ext in ((v['file'], 'mp4'), (v['srt'], 'srt')):
        dst = stage / f"{v['name']}.{ext}"
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            dst.write_bytes(src.read_bytes())
        assets.append(dst)
    if subprocess.run(['gh', 'release', 'view', TAG, '--repo', GH], capture_output=True).returncode:
        notes = stage / 'RELEASE.md'
        notes.write_text('Claude Mods em vídeo — avatar e voz do Nei, animações explicativas sincronizadas à fala e legendas.\n\n'
                         f'Assistir: {PAGES}videos/\n\nInspiração: {FONTE}\n\n'
                         'Produção: https://inematds.github.io/explicavideos/guia/ (Explicavideos v2)\n\n'
                         f'- Completo: {d}')
        sh('gh', 'release', 'create', TAG, '--repo', GH, '--draft', '--title', 'Claude Mods em vídeo (v2)', '--notes-file', str(notes))
    have = {a['name']: a['size'] for a in json.loads(sh('gh', 'release', 'view', TAG, '--repo', GH, '--json', 'assets'))['assets']}
    for f in assets:
        if have.get(f.name) != f.stat().st_size:
            print('upload', f.name, flush=True); sh('gh', 'release', 'upload', TAG, str(f), '--repo', GH, '--clobber')
    folder = REPO / 'videos'; folder.mkdir(exist_ok=True)
    (folder / 'completo.vtt').write_text('WEBVTT\n\n' + re.sub(r'(\d\d:\d\d:\d\d),(\d{3})', r'\1.\2', v['srt'].read_text()))
    caps = ''.join(f'<button type="button" data-time="{s}">{s // 60:02d}:{s % 60:02d} · {html.escape(c)}</button>' for s, c in v['chapters'])
    page = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Mods em vídeo · INEMA.CLUB</title><meta name="description" content="Vídeo explicativo com avatar do Nei: o que são os Mods do Claude Code, como funcionam por eventos, exemplos e como criar o seu.">
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0D1321;color:#F0EBD8;font:18px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:32px 16px}}
a{{color:#FFC300}}h1{{font-size:clamp(1.8rem,5vw,2.8rem);line-height:1.15;margin:.4em 0}}h1 b{{color:#FFC300}}.lead{{color:#b9c3d0;max-width:780px}}
.card{{background:#1D2D44;border:1px solid #3E5C76;border-radius:16px;padding:20px;margin:28px 0}}.card h2{{margin:0 0 4px;font-size:1.3rem}}.card h2 span{{color:#748CAB;font-size:1rem;font-weight:500}}.meta{{color:#b9c3d0;margin:0 0 12px}}
video{{width:100%;aspect-ratio:16/9;background:#0a0f19;border-radius:12px}}
summary{{cursor:pointer;color:#FFC300;margin-top:8px}}button{{display:block;background:#0D1321;color:#F0EBD8;border:1px solid #3E5C76;border-radius:8px;padding:10px 12px;margin:6px 0;text-align:left;cursor:pointer;width:100%;font:inherit;font-size:16px}}
:focus-visible{{outline:3px solid #FFC300;outline-offset:3px}}footer{{color:#748CAB;font-size:15px;margin-top:40px}}</style></head>
<body><main><nav><a href="https://inema.club">INEMA.CLUB</a> · <a href="https://github.com/{GH}">GitHub</a></nav>
<h1>Claude Mods: <b>o Claude Code que você mesmo muda.</b></h1>
<p class="lead">Vídeo explicativo com avatar e voz do Nei: o que é um mod, como ele funciona por eventos (observar, alterar ou assumir), cinco exemplos, como criar o seu conversando com o Claude Code e os cuidados — temporário até virar plugin, fonte confiável e consumo de cota.</p>
<section class="card" id="completo"><h2>Completo <span>{d}</span></h2>
<video controls preload="metadata" playsinline><source src="{BASE}{v["name"]}.mp4" type="video/mp4"><track default kind="subtitles" src="completo.vtt" srclang="pt" label="Português"></video>
<p><a href="{BASE}{v["name"]}.mp4">Baixar MP4</a> · <a href="{BASE}{v["name"]}.srt">Baixar legendas</a></p>
<details open><summary>Capítulos</summary>{caps}</details></section>
<footer>Produzido com o <a href="https://inematds.github.io/explicavideos/guia/">Explicavideos v2</a>. Exemplos inspirados no <a href="{FONTE}">vídeo do Tristan sobre Claude Mods</a>. Recurso educacional independente, não é produto da Anthropic. Conteúdo aberto do <a href="https://inema.club">INEMA.CLUB</a>.</footer></main>
<script>document.querySelectorAll('[data-time]').forEach(b=>b.addEventListener('click',()=>{{const v=b.closest('.card').querySelector('video');v.currentTime=Number(b.dataset.time);v.play();}}));</script></body></html>
'''
    (folder / 'index.html').write_text(page)
    (REPO / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Claude Mods em vídeo</title><meta http-equiv="refresh" content="0; url=videos/"><a href="videos/">Assistir</a>\n')
    (folder / 'delivery.json').write_text(json.dumps({'completo': {'url': BASE + v['name'] + '.mp4', 'srt': BASE + v['name'] + '.srt', 'duration': round(v['duration'], 2)}}, indent=2) + '\n')
    g = lambda *a: sh('git', '-c', 'user.name=inematds', '-c', 'user.email=inematds@gmail.com', *a, cwd=REPO)
    g('add', '-A')
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO).returncode:
        g('commit', '-m', 'feat: Claude Mods em vídeo (v2)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
        g('push', '-q', 'origin', 'HEAD:main')
    sh('gh', 'release', 'edit', TAG, '--repo', GH, '--draft=false')
    with urllib.request.urlopen(urllib.request.Request(BASE + v['name'] + '.mp4', method='HEAD'), timeout=60) as r:
        assert r.status == 200
    for _ in range(40):
        try:
            with urllib.request.urlopen(PAGES + 'videos/delivery.json?v=' + str(int(time.time())), timeout=30) as f:
                if 'completo' in f.read().decode():
                    break
        except Exception:
            pass
        time.sleep(30)
    else:
        sys.exit('push e release feitos; Pages ainda não respondeu')
    print('OK', PAGES + 'videos/')


if __name__ == '__main__':
    main()
