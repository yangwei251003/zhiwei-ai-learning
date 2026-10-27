import hljs from 'highlight.js/lib/common'
import markdownit from 'markdown-it'

const md = markdownit({
  html: false,
  linkify: true,
  typographer: false,
  highlight(source, language) {
    if (language && hljs.getLanguage(language)) {
      return `<pre><code class="hljs language-${language}">${hljs.highlight(source, { language }).value}</code></pre>`
    }
    return `<pre><code>${md.utils.escapeHtml(source)}</code></pre>`
  },
})

const defaultLinkOpen = md.renderer.rules.link_open || ((tokens, index, options, _env, self) => self.renderToken(tokens, index, options))
md.renderer.rules.link_open = (tokens, index, options, env, self) => {
  tokens[index].attrSet('target', '_blank')
  tokens[index].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, index, options, env, self)
}

export const renderMarkdown = (source = '') => md.render(source)
