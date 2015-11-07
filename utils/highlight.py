# coding: utf-8

"""
    mistune_contrib.highlight
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    Support highlight code features for mistune.
    :copyright: (c) 2014 - 2015 by Hsiaoming Yang.
"""

import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html


def block_code(text, lang, inlinestyles=False, linenos=False):
    if not lang:
        text = text.strip()
        return u'<pre><code>%s</code></pre>\n' % mistune.escape(text)

    try:
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = html.HtmlFormatter(
            noclasses=inlinestyles, linenos=linenos
        )
        code = highlight(text, lexer, formatter)
        if linenos:
            return '<div class="highlight-wrapper">%s</div>\n' % code
        return code
    except:
        return '<pre class="%s"><code >%s</code></pre>\n' % (
            lang, mistune.escape(text)
        )


class HighlightMixin(mistune.Renderer):
    def block_code(self, text, lang):
        # renderer has an options
        inlinestyles = self.options.get('inlinestyles')
        linenos = self.options.get('linenos')
        return block_code(text, lang, inlinestyles, linenos)


def parse2markdown(text):
    renderer = HighlightMixin()
    markdown = mistune.Markdown(renderer=renderer)
    return markdown(text)


