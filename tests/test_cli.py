"""
Tests the Grip command-line interface.
"""

from __future__ import print_function, unicode_literals

import sys
from subprocess import PIPE, STDOUT, CalledProcessError, Popen

import pytest

from grip.command import main, usage, version


if sys.version_info[0] == 2 and sys.version_info[1] < 7:
    class CalledProcessError(CalledProcessError):
        def __init__(self, returncode, cmd, output):
            super(CalledProcessError, self).__init__(returncode, cmd)
            self.output = output


def run(*args, **kwargs):
    command = kwargs.pop('command', 'grip')
    stdin = kwargs.pop('stdin', None)

    cmd = [command] + list(args)
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
              universal_newlines=True)
    # Sent input as STDIN then close it
    output, _ = p.communicate(input=stdin)
    p.stdin.close()
    # Wait for process to terminate
    returncode = p.wait()
    # Raise exception on failed process calls
    if returncode != 0:
        raise CalledProcessError(returncode, cmd, output=output)
    return output


def test_help():
    assert run('-h') == usage
    assert run('--help') == usage


def test_version():
    assert run('-V') == version + '\n'
    assert run('--version') == version + '\n'


def test_bad_command():
    simple_usage = '\n\n'.join(usage.split('\n\n')[:1])
    with pytest.raises(CalledProcessError) as excinfo:
        run('--does-not-exist')
    assert excinfo.value.output == simple_usage + '\n'


@pytest.mark.parametrize('online', [False, True])
@pytest.mark.parametrize('exporting', [False, True])
def test_rendering_mode(monkeypatch, online, exporting):
    calls = []

    def capture(*args):
        calls.append(args)

    monkeypatch.setattr('grip.command.serve', capture)
    monkeypatch.setattr('grip.command.export', capture)
    args = ['README.md']
    if online:
        args.append('--online')
    if exporting:
        args.append('--export')
    assert main(args) == 0
    assert len(calls) == 1
    assert calls[0][5 if exporting else 7] is (not online)


@pytest.mark.parametrize('inline', [False, True])
def test_offline_export(monkeypatch, tmpdir, inline):
    def unexpected_request(*args, **kwargs):
        pytest.fail('Offline export must not send HTTP requests')

    monkeypatch.setattr(
        'requests.sessions.Session.request', unexpected_request)
    source = tmpdir.join('README.md')
    source.write('# Hello\n\n**Offline**\n\n'
                 '| A | B |\n| --- | --- |\n| 1 | 2 |\n\n'
                 '```python\nprint("hello")\n```\n')
    target = tmpdir.join('index.html')
    args = [str(source), '--export', str(target)]
    if not inline:
        args.append('--no-inline')
    assert main(args) == 0
    html = target.read()
    assert '<h1 id="hello">Hello</h1>' in html
    assert '<strong>Offline</strong>' in html
    assert '<table>' in html
    assert 'class="highlight"' in html
    assert '--page-bg:' in html


def test_offline_preview(monkeypatch):
    from flask import url_for
    from grip import create_app

    def unexpected_request(*args, **kwargs):
        pytest.fail('Offline preview must not send HTTP requests')

    monkeypatch.setattr(
        'requests.sessions.Session.request', unexpected_request)
    app = create_app(text='# Preview', render_offline=True)
    app.testing = True
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'<h1 id="preview">Preview</h1>' in response.data
        assert b'--page-bg:' in response.data
        with app.test_request_context():
            stylesheet_url = url_for('static', filename='offline.css')
        assert client.get(stylesheet_url).status_code == 200


@pytest.mark.parametrize('inline', [False, True])
def test_mermaid_export(monkeypatch, tmpdir, inline):
    from helpers import input_filename

    def unexpected_request(*args, **kwargs):
        pytest.fail('Mermaid export must not send HTTP requests')

    monkeypatch.setattr(
        'requests.sessions.Session.request', unexpected_request)
    target = tmpdir.join('mermaid.html')
    args = [input_filename('mermaid.md'), '--export', str(target)]
    if not inline:
        args.append('--no-inline')
    assert main(args) == 0
    html = target.read()
    assert html.count('<pre class="mermaid">') == 3
    assert 'mermaid.min.js"' not in html
    assert len(html) > 2000000
    assert 'mermaid.initialize' in html
    assert 'securityLevel: \'strict\'' in html


# TODO: Figure out how to run the CLI and still capture requests
# TODO: Test all Grip CLI commands and arguments
# TODO: Test settings wire-up (settings.py, settings_local.py, ~/.grip)

# TODO: Test `cat README.md | ~/.local/bin/grip - --export -` (#152)
