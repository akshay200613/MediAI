/**
 * Unit tests for MarkdownRenderer.tsx
 */

import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer'
import type { Citation } from '@/types/chat'

describe('MarkdownRenderer', () => {
  it('renders tables wrapped in overflow-x-auto container', () => {
    const markdown = `
| Department | Doctor | Timings |
| :--- | :---: | ---: |
| Cardiology | Dr. Sarah | 9 AM - 1 PM |
| Neurology | Dr. Roy | 2 PM - 5 PM |
`
    const { container } = render(<MarkdownRenderer content={markdown} />)

    // Check table exists
    const table = container.querySelector('table')
    expect(table).not.toBeNull()

    // Check wrapper has overflow-x-auto for smaller screen responsiveness
    const overflowWrapper = container.querySelector('.overflow-x-auto')
    expect(overflowWrapper).not.toBeNull()

    // Check headers and rows
    expect(screen.getByText('Department')).toBeDefined()
    expect(screen.getByText('Doctor')).toBeDefined()
    expect(screen.getByText('Timings')).toBeDefined()
    expect(screen.getByText('Cardiology')).toBeDefined()
    expect(screen.getByText('Dr. Sarah')).toBeDefined()
    expect(screen.getByText('Neurology')).toBeDefined()
  })

  it('renders headings h1, h2, h3, h4 with appropriate styles', () => {
    const markdown = `
# Hospital Overview
## Available Specialties
### Department Details
#### Working Hours
`
    const { container } = render(<MarkdownRenderer content={markdown} />)

    expect(container.querySelector('h1')?.textContent).toContain('Hospital Overview')
    expect(container.querySelector('h2')?.textContent).toContain('Available Specialties')
    expect(container.querySelector('h3')?.textContent).toContain('Department Details')
    expect(container.querySelector('h4')?.textContent).toContain('Working Hours')
  })

  it('renders paragraphs with comfortable spacing', () => {
    const markdown = 'This is a clear clinical description of the patient symptoms and recommended steps.'
    render(<MarkdownRenderer content={markdown} />)

    const paragraph = screen.getByText(/This is a clear clinical description/)
    expect(paragraph).toBeDefined()
    expect(paragraph.tagName.toLowerCase()).toBe('p')
  })

  it('renders unordered and ordered lists', () => {
    const markdown = `
- Routine checkup
- Blood tests
- Follow-up consultation

1. Arrive 15 minutes early
2. Bring prior records
`
    const { container } = render(<MarkdownRenderer content={markdown} />)

    expect(container.querySelector('ul')).not.toBeNull()
    expect(screen.getByText('Routine checkup')).toBeDefined()
    expect(screen.getByText('Blood tests')).toBeDefined()

    expect(container.querySelector('ol')).not.toBeNull()
    expect(screen.getByText('Arrive 15 minutes early')).toBeDefined()
    expect(screen.getByText('Bring prior records')).toBeDefined()
  })

  it('renders multi-line code blocks and inline code', () => {
    const markdown = 'Use `dosage: 500mg` as instructed.\n\n```python\ndef prescribe():\n    return "500mg"\n```'
    const { container } = render(<MarkdownRenderer content={markdown} />)

    // Inline code
    const inlineCode = screen.getByText('dosage: 500mg')
    expect(inlineCode.tagName.toLowerCase()).toBe('code')

    // Fenced code block
    const codeBlock = container.querySelector('pre code')
    expect(codeBlock).not.toBeNull()
    expect(codeBlock?.textContent).toContain('def prescribe():')
  })

  it('renders blockquotes', () => {
    const markdown = '> Important Note: Please verify insurance coverage with your TPA prior to admission.'
    const { container } = render(<MarkdownRenderer content={markdown} />)

    const blockquote = container.querySelector('blockquote')
    expect(blockquote).not.toBeNull()
    expect(blockquote?.textContent).toContain('Important Note:')
  })

  it('renders markdown links with security attributes', () => {
    const markdown = 'Visit [BMH Portal](https://bmh.example.com) for more details.'
    render(<MarkdownRenderer content={markdown} />)

    const link = screen.getByRole('link', { name: /BMH Portal/ })
    expect(link.getAttribute('href')).toBe('https://bmh.example.com')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('transforms [Source1][Source2] into structured interactive buttons and fires callback on click', () => {
    const mockCitations: Citation[] = [
      {
        id: 'chunk-1',
        documentName: 'BMH Hospital Guide',
        excerpt: 'BMH Kozhikode is a 800-bed multi-specialty hospital.',
        retrievalMethod: 'hybrid',
        score: 0.94,
      },
      {
        id: 'chunk-2',
        documentName: 'Insurance & TPA Empanelment',
        excerpt: 'Cashless facility available with Star Health, ICICI Lombard.',
        retrievalMethod: 'hybrid',
        score: 0.91,
      },
    ]

    const onSelectCitation = vi.fn()
    const markdown = 'The hospital has 800 beds [Source 1][Source 2] with emergency services available.'

    render(
      <MarkdownRenderer
        content={markdown}
        citations={mockCitations}
        onSelectCitation={onSelectCitation}
      />
    )

    // Verify structured citation buttons are rendered instead of plain text
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(2)

    // First citation button
    expect(buttons[0].textContent).toContain('[1]')
    expect(buttons[0].getAttribute('title')).toBe('BMH Hospital Guide')

    // Second citation button
    expect(buttons[1].textContent).toContain('[2]')
    expect(buttons[1].getAttribute('title')).toBe('Insurance & TPA Empanelment')

    // Clicking fires the citation selection callback with matching citation ID
    fireEvent.click(buttons[0])
    expect(onSelectCitation).toHaveBeenCalledWith('chunk-1', mockCitations)

    fireEvent.click(buttons[1])
    expect(onSelectCitation).toHaveBeenCalledWith('chunk-2', mockCitations)
  })
})
