import { describe, expect, it } from 'vitest'
import { renderPetMarkdown } from './petMarkdown'

describe('renderPetMarkdown', () => {
  it('returns empty string for falsy input', () => {
    expect(renderPetMarkdown('')).toBe('')
  })

  it('escapes HTML to prevent injection', () => {
    expect(renderPetMarkdown('<script>alert(1)</script>')).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt;',
    )
  })

  it('renders bold, italic, and inline code', () => {
    const html = renderPetMarkdown('**bold** and *italic* with `code`')
    expect(html).toContain('<strong>bold</strong>')
    expect(html).toContain('<em>italic</em>')
    expect(html).toContain('<code>code</code>')
  })

  it('renders line breaks and list items', () => {
    const html = renderPetMarkdown('line one\n- item one\n- item two')
    expect(html).toContain('line one')
    expect(html).toContain('class="md-list-item"')
    expect(html).toContain('item one')
    expect(html).toContain('item two')
  })

  it('renders standalone line breaks', () => {
    expect(renderPetMarkdown('line one\nline two')).toContain('line one<br>line two')
  })
})