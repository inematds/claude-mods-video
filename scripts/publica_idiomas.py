"""Publica as versões EN/ES do vídeo Claude Mods (v2) em inematds/claude-mods-video, sem mexer no vídeo PT.
Release video-v2.0.0: claude-mods-completo-16x9-{en,es}.mp4/.srt.
Pages: videos/en/ e videos/es/ (mesmo visual da página PT), seletor PT · EN · ES nas três páginas e delivery.json com os três idiomas.
Idempotente: sobe só o que mudou de tamanho; commit só se houver diff. Adaptado de iacultivada-video/publica_idiomas.py."""
import html, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

OUT = Path.home() / 'projetos/output/claude-mods-video'
REPO = Path.home() / 'projetos/claude-mods-video'
GH, TAG = 'inematds/claude-mods-video', 'video-v2.0.0'
BASE = f'https://github.com/{GH}/releases/download/{TAG}/'
PAGES = 'https://inematds.github.io/claude-mods-video/'
FONTE = 'https://www.youtube.com/watch?v=LDn7rQKIFro'
LANGS = ['pt', 'en', 'es']
T = {
    'en': dict(title='Claude Mods on video', h1='Claude Mods: <b>Claude Code, customized by you.</b>', track='English',
               desc='Explainer video with Nei’s avatar: what Claude Code Mods are, how they work through events, examples, and how to create your own.',
               lead='Explainer video with Nei’s avatar and voice: what a mod is, how it works through events (observe, change, or take over), five examples, how to create your own by talking to Claude Code, and the precautions — temporary until it becomes a plugin, trusted sources only, and usage limits.',
               card='Full video', mp4='Download MP4', srt='Download subtitles', cap='Chapters',
               foot=f'Made with <a href="https://inematds.github.io/explicavideos/guia/">Explicavideos v2</a>. Examples inspired by <a href="{FONTE}">Tristan’s video about Claude Mods</a>. Independent educational resource, not an Anthropic product. Open content from <a href="https://inema.club">INEMA.CLUB</a>.'),
    'es': dict(title='Claude Mods en video', h1='Claude Mods: <b>el Claude Code que tú mismo cambias.</b>', track='Español',
               desc='Video explicativo con el avatar de Nei: qué son los Mods de Claude Code, cómo funcionan por eventos, ejemplos y cómo crear el tuyo.',
               lead='Video explicativo con el avatar y la voz de Nei: qué es un mod, cómo funciona por eventos (observar, modificar o asumir), cinco ejemplos, cómo crear el tuyo conversando con Claude Code y las precauciones: temporal hasta convertirse en plugin, solo de fuentes confiables y consumo del límite.',
               card='Completo', mp4='Descargar MP4', srt='Descargar subtítulos', cap='Capítulos',
               foot=f'Producido con <a href="https://inematds.github.io/explicavideos/guia/">Explicavideos v2</a>. Ejemplos inspirados en el <a href="{FONTE}">video de Tristan sobre Claude Mods</a>. Recurso educativo independiente, no es un producto de Anthropic. Contenido abierto de <a href="https://inema.club">INEMA.CLUB</a>.'),
}


def sh(*a, **kw):
    return subprocess.run(a, check=True, text=True, capture_output=True, **kw).stdout


def decode_ok(p):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'null', '-'], capture_output=True, text=True).stderr.strip() == ''


def seletor(lang, prefixo):
    rot = {'pt': 'PT', 'en': 'EN', 'es': 'ES'}; dest = {'pt': '', 'en': 'en/', 'es': 'es/'}
    itens = [f'<b>{rot[l]}</b>' if l == lang else f'<a href="{prefixo}{dest[l]}" hreflang="{l}">{rot[l]}</a>' for l in LANGS]
    return '<span style="float:right">' + ' · '.join(itens) + '</span>'


def main():
    vids, stage = {}, OUT / 'release'
    stage.mkdir(exist_ok=True)
    for lang in ('en', 'es'):
        v2 = OUT / f'{lang}-v2'
        rec = json.loads((v2 / f'verification/assembled-{lang}.json').read_text())
        src = Path(rec['file'])
        assert src.stat().st_size == rec['bytes'] and (v2 / f'verification/decode-full-{lang}.log').read_text() == '' and decode_ok(src), src
        for b in rec['blocks']:
            assert json.loads((v2 / f'final/{b}/alignment.json').read_text())['ratio'] > .90, b
        scenes = json.loads((v2 / f'docs/lesson-{lang}.json').read_text())
        assert len(rec['chapters']) == len(scenes)
        caps = ''.join(f'<button type="button" data-time="{int(c["time"])}">{int(c["time"]) // 60:02d}:{int(c["time"]) % 60:02d} · '
                       f'{html.escape(scenes[c["scene"] - 1]["title"])}</button>' for c in rec['chapters'])
        name = f'claude-mods-completo-16x9-{lang}'
        files = []
        for s, ext in ((src, 'mp4'), (src.with_suffix('.srt'), 'srt')):
            dst = stage / f'{name}.{ext}'
            if not dst.exists() or dst.stat().st_size != s.stat().st_size:
                dst.write_bytes(s.read_bytes())
            files.append(dst)
        dur = float(sh('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(src)))
        vids[lang] = dict(name=name, files=files, duration=dur, caps=caps)
    have = {a['name']: a['size'] for a in json.loads(sh('gh', 'release', 'view', TAG, '--repo', GH, '--json', 'assets'))['assets']}
    for v in vids.values():
        for f in v['files']:
            if have.get(f.name) != f.stat().st_size:
                print('upload', f.name, flush=True); sh('gh', 'release', 'upload', TAG, str(f), '--repo', GH, '--clobber')
    folder = REPO / 'videos'
    pt = (folder / 'index.html').read_text()
    style = re.search(r'<style>.*?</style>', pt, re.S).group(0)
    for lang, v in vids.items():
        t = T[lang]; d = f"{int(v['duration'] // 60)}min{int(v['duration'] % 60):02d}s"; sub = folder / lang; sub.mkdir(exist_ok=True)
        (sub / 'completo.vtt').write_text('WEBVTT\n\n' + re.sub(r'(\d\d:\d\d:\d\d),(\d{3})', r'\1.\2', v['files'][1].read_text()))
        url, srt = BASE + v['name'] + '.mp4', BASE + v['name'] + '.srt'
        page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
                f'<title>{t["title"]} · INEMA.CLUB</title><meta name="description" content="{html.escape(t["desc"])}">\n'
                + ''.join(f'<link rel="alternate" hreflang="{l}" href="{PAGES}videos/{"" if l == "pt" else l + "/"}">' for l in LANGS) + f'\n{style}</head>\n'
                f'<body><main><nav>{seletor(lang, "../")}<a href="https://inema.club">INEMA.CLUB</a> · <a href="https://github.com/{GH}">GitHub</a></nav>\n'
                f'<h1>{t["h1"]}</h1>\n<p class="lead">{html.escape(t["lead"])}</p>\n'
                f'<section class="card" id="completo"><h2>{t["card"]} <span>{d}</span></h2>\n'
                f'<video controls preload="metadata" playsinline><source src="{url}" type="video/mp4"><track default kind="subtitles" src="completo.vtt" srclang="{lang}" label="{t["track"]}"></video>\n'
                f'<p><a href="{url}">{t["mp4"]}</a> · <a href="{srt}">{t["srt"]}</a></p>\n'
                f'<details open><summary>{t["cap"]}</summary>{v["caps"]}</details></section>\n'
                f'<footer>{t["foot"]}</footer></main>\n'
                "<script>document.querySelectorAll('[data-time]').forEach(b=>b.addEventListener('click',()=>{const v=b.closest('.card').querySelector('video');v.currentTime=Number(b.dataset.time);v.play();}));</script></body></html>\n")
        (sub / 'index.html').write_text(page)
    if 'hreflang="en"' not in pt:
        pt = pt.replace('<nav>', '<nav>' + seletor('pt', ''), 1); (folder / 'index.html').write_text(pt)
    dj = folder / 'delivery.json'; deliv = json.loads(dj.read_text())
    for lang, v in vids.items():
        deliv[lang] = {'url': BASE + v['name'] + '.mp4', 'srt': BASE + v['name'] + '.srt', 'duration': round(v['duration'], 2)}
    dj.write_text(json.dumps(deliv, indent=2) + '\n')
    g = lambda *a: sh('git', '-c', 'user.name=inematds', '-c', 'user.email=inematds@gmail.com', *a, cwd=REPO)
    g('add', 'videos', 'scripts', 'README.md')
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO).returncode:
        g('commit', '-m', 'feat: Claude Mods em vídeo em inglês e espanhol (videos/en, videos/es) + seletor de idioma\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
        g('push', '-q', 'origin', 'HEAD:main')
    for v in vids.values():
        with urllib.request.urlopen(urllib.request.Request(BASE + v['name'] + '.mp4', method='HEAD'), timeout=60) as r:
            assert r.status == 200
    for lang, v in vids.items():
        for _ in range(40):
            try:
                with urllib.request.urlopen(f'{PAGES}videos/{lang}/?v={int(time.time())}', timeout=30) as f:
                    if v['name'] in f.read().decode():
                        break
            except Exception:
                pass
            time.sleep(30)
        else:
            sys.exit(f'push e release feitos; Pages ({lang}) ainda não respondeu')
        print('OK', f'{PAGES}videos/{lang}/')


if __name__ == '__main__':
    main()
