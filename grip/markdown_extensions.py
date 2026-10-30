from xml.sax.saxutils import escape

from markdown.extensions import Extension
from markdown.extensions.fenced_code import FencedBlockPreprocessor
from markdown.preprocessors import Preprocessor


class MermaidPreprocessor(Preprocessor):
    def run(self, lines):
        def replace(match):
            if (match.group('lang') or '').lower() != 'mermaid':
                return match.group(0)
            html = '<pre class="mermaid">{0}</pre>'.format(
                escape(match.group('code')))
            return '\n' + self.md.htmlStash.store(html) + '\n'

        # Reuse Markdown's fence parser so code inside other fences stays code.
        return FencedBlockPreprocessor.FENCED_BLOCK_RE.sub(
            replace, '\n'.join(lines)).split('\n')


class MermaidExtension(Extension):
    def extendMarkdown(self, md, md_globals=None):
        processor = MermaidPreprocessor(md)
        if hasattr(md.preprocessors, 'register'):
            md.preprocessors.register(processor, 'grip_mermaid', 26)
        else:
            md.preprocessors.add('grip_mermaid', processor, '<fenced_code')
