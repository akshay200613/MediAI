'use client'

import React from 'react'
import { FileText, ExternalLink, Check, Copy } from 'lucide-react'
import type { Citation } from '@/types/chat'

interface MarkdownRendererProps {
  content: string
  citations?: Citation[]
  onSelectCitation?: (citationId: string, citations: Citation[]) => void
}

type Alignment = 'left' | 'center' | 'right'

interface TableData {
  headers: string[]
  alignments: Alignment[]
  rows: string[][]
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  citations = [],
  onSelectCitation,
}) => {
  if (!content) return null

  // Process text into block tokens (tables, code blocks, headings, blockquotes, lists, paragraphs)
  const blocks = parseMarkdownBlocks(content)

  return (
    <div className="space-y-3 text-xs sm:text-sm text-slate-200 leading-relaxed font-sans min-w-0">
      {blocks.map((block, idx) => renderBlock(block, idx, citations, onSelectCitation))}
    </div>
  )
}

// ── Block Types ─────────────────────────────────────────────────────────────

type Block =
  | { type: 'heading'; level: number; text: string }
  | { type: 'table'; data: TableData }
  | { type: 'codeblock'; language: string; code: string }
  | { type: 'blockquote'; lines: string[] }
  | { type: 'unordered_list'; items: string[] }
  | { type: 'ordered_list'; start: number; items: string[] }
  | { type: 'paragraph'; text: string }

// ── Parser ──────────────────────────────────────────────────────────────────

function parseMarkdownBlocks(text: string): Block[] {
  const lines = text.split(/\r?\n/)
  const blocks: Block[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // 1. Skip empty lines
    if (!line.trim()) {
      i++
      continue
    }

    // 2. Code blocks (```lang ... ```)
    if (line.trim().startsWith('```')) {
      const match = line.trim().match(/^```([a-zA-Z0-9_-]*)/)
      const language = match ? match[1] : ''
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      if (i < lines.length && lines[i].trim().startsWith('```')) {
        i++ // consume closing ```
      }
      blocks.push({
        type: 'codeblock',
        language,
        code: codeLines.join('\n'),
      })
      continue
    }

    // 3. Headings (# H1, ## H2, ### H3, #### H4, ##### H5, ###### H6)
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      })
      i++
      continue
    }

    // 4. Blockquotes (> ...)
    if (line.trim().startsWith('>')) {
      const quoteLines: string[] = []
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''))
        i++
      }
      blocks.push({
        type: 'blockquote',
        lines: quoteLines,
      })
      continue
    }

    // 5. Tables: header row has pipes, followed by delimiter row |---|---|
    if (isTableStart(lines, i)) {
      const headerLine = lines[i]
      const delimiterLine = lines[i + 1]
      const { headers, alignments } = parseTableHeaderAndAlignments(headerLine, delimiterLine)
      i += 2

      const rows: string[][] = []
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(parseTableRow(lines[i], headers.length))
        i++
      }

      blocks.push({
        type: 'table',
        data: { headers, alignments, rows },
      })
      continue
    }

    // 6. Unordered lists (- item, * item, + item)
    if (isUnorderedListItem(line)) {
      const items: string[] = []
      while (i < lines.length && isUnorderedListItem(lines[i])) {
        items.push(cleanListItem(lines[i]))
        i++
      }
      blocks.push({
        type: 'unordered_list',
        items,
      })
      continue
    }

    // 7. Ordered lists (1. item, 2. item)
    if (isOrderedListItem(line)) {
      const match = line.trim().match(/^(\d+)\.\s+(.*)$/)
      const start = match ? parseInt(match[1], 10) : 1
      const items: string[] = []
      while (i < lines.length && isOrderedListItem(lines[i])) {
        const itemMatch = lines[i].trim().match(/^\d+\.\s+(.*)$/)
        items.push(itemMatch ? itemMatch[1] : lines[i])
        i++
      }
      blocks.push({
        type: 'ordered_list',
        start,
        items,
      })
      continue
    }

    // 8. Normal Paragraph (accumulate consecutive text lines)
    const paragraphLines: string[] = [line]
    i++
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('```') &&
      !lines[i].match(/^#{1,6}\s+/) &&
      !lines[i].trim().startsWith('>') &&
      !isTableStart(lines, i) &&
      !isUnorderedListItem(lines[i]) &&
      !isOrderedListItem(lines[i])
    ) {
      paragraphLines.push(lines[i])
      i++
    }

    blocks.push({
      type: 'paragraph',
      text: paragraphLines.join(' '),
    })
  }

  return blocks
}

// ── Table Helpers ───────────────────────────────────────────────────────────

function isTableStart(lines: string[], index: number): boolean {
  if (index + 1 >= lines.length) return false
  const header = lines[index].trim()
  const delimiter = lines[index + 1].trim()

  if (!header.includes('|') || !delimiter.includes('|')) return false
  // Check if delimiter line looks like: | --- | :---: | ---: |
  return /^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?$/.test(delimiter)
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim()
  return trimmed.startsWith('|') || (trimmed.includes('|') && trimmed.endsWith('|'))
}

function parseTableRow(line: string, expectedCount: number): string[] {
  let cleaned = line.trim()
  if (cleaned.startsWith('|')) cleaned = cleaned.slice(1)
  if (cleaned.endsWith('|')) cleaned = cleaned.slice(0, -1)

  const cells = cleaned.split('|').map((c) => c.trim())
  while (cells.length < expectedCount) cells.push('')
  return cells.slice(0, expectedCount)
}

function parseTableHeaderAndAlignments(
  headerLine: string,
  delimiterLine: string
): { headers: string[]; alignments: Alignment[] } {
  let hClean = headerLine.trim()
  if (hClean.startsWith('|')) hClean = hClean.slice(1)
  if (hClean.endsWith('|')) hClean = hClean.slice(0, -1)
  const headers = hClean.split('|').map((h) => h.trim())

  let dClean = delimiterLine.trim()
  if (dClean.startsWith('|')) dClean = dClean.slice(1)
  if (dClean.endsWith('|')) dClean = dClean.slice(0, -1)
  const dCells = dClean.split('|').map((d) => d.trim())

  const alignments: Alignment[] = dCells.map((cell) => {
    const left = cell.startsWith(':')
    const right = cell.endsWith(':')
    if (left && right) return 'center'
    if (right) return 'right'
    return 'left'
  })

  while (alignments.length < headers.length) {
    alignments.push('left')
  }

  return { headers, alignments }
}

function isUnorderedListItem(line: string): boolean {
  return /^(\s*[-*+]\s+)/.test(line)
}

function isOrderedListItem(line: string): boolean {
  return /^(\s*\d+\.\s+)/.test(line)
}

function cleanListItem(line: string): string {
  return line.trim().replace(/^[-*+]\s+/, '')
}

// ── Render Block ────────────────────────────────────────────────────────────

function renderBlock(
  block: Block,
  key: number,
  citations: Citation[],
  onSelectCitation?: (id: string, citations: Citation[]) => void
): React.ReactNode {
  switch (block.type) {
    case 'heading': {
      const inline = renderInline(block.text, citations, onSelectCitation)
      if (block.level === 1) {
        return (
          <h1 key={key} className="text-base sm:text-lg font-bold text-slate-100 mt-4 mb-2 pb-1.5 border-b border-slate-800 flex items-center gap-2">
            {inline}
          </h1>
        )
      }
      if (block.level === 2) {
        return (
          <h2 key={key} className="text-sm sm:text-base font-bold text-teal-200 mt-3.5 mb-2 pb-1 border-b border-slate-800/80">
            {inline}
          </h2>
        )
      }
      if (block.level === 3) {
        return (
          <h3 key={key} className="text-xs sm:text-sm font-semibold text-teal-300 mt-3 mb-1.5">
            {inline}
          </h3>
        )
      }
      return (
        <h4 key={key} className="text-xs sm:text-sm font-semibold text-slate-200 mt-2.5 mb-1">
          {inline}
        </h4>
      )
    }

    case 'table': {
      const { headers, alignments, rows } = block.data
      return (
        <div
          key={key}
          className="overflow-x-auto my-3 rounded-xl border border-slate-800 bg-slate-900/60 shadow-inner max-w-full"
        >
          <table className="w-full text-left text-xs border-collapse min-w-[320px]">
            <thead>
              <tr className="bg-slate-800/80 border-b border-slate-700/80">
                {headers.map((h, i) => (
                  <th
                    key={i}
                    className={`px-3.5 py-2.5 font-semibold text-[11px] text-teal-300 uppercase tracking-wider ${
                      alignments[i] === 'center'
                        ? 'text-center'
                        : alignments[i] === 'right'
                        ? 'text-right'
                        : 'text-left'
                    }`}
                  >
                    {renderInline(h, citations, onSelectCitation)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="hover:bg-slate-800/30 transition-colors even:bg-slate-900/40"
                >
                  {row.map((cell, cIdx) => (
                    <td
                      key={cIdx}
                      className={`px-3.5 py-2.5 text-slate-200 text-xs sm:text-sm ${
                        alignments[cIdx] === 'center'
                          ? 'text-center'
                          : alignments[cIdx] === 'right'
                          ? 'text-right'
                          : 'text-left'
                      }`}
                    >
                      {renderInline(cell, citations, onSelectCitation)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    case 'codeblock': {
      return (
        <CodeBlockContainer
          key={key}
          language={block.language}
          code={block.code}
        />
      )
    }

    case 'blockquote': {
      return (
        <blockquote
          key={key}
          className="border-l-4 border-teal-500/70 bg-teal-950/20 px-3.5 py-2.5 my-2.5 rounded-r-xl text-xs sm:text-sm italic text-slate-300 leading-relaxed shadow-xs"
        >
          {block.lines.map((line, lIdx) => (
            <p key={lIdx} className={lIdx > 0 ? 'mt-1.5' : ''}>
              {renderInline(line, citations, onSelectCitation)}
            </p>
          ))}
        </blockquote>
      )
    }

    case 'unordered_list': {
      return (
        <ul key={key} className="space-y-1.5 my-2.5 pl-1">
          {block.items.map((item, iIdx) => (
            <li key={iIdx} className="flex items-start gap-2.5 text-xs sm:text-sm text-slate-200">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 mt-2 shrink-0 shadow-xs shadow-teal-400/50" />
              <div className="flex-1 min-w-0">
                {renderInline(item, citations, onSelectCitation)}
              </div>
            </li>
          ))}
        </ul>
      )
    }

    case 'ordered_list': {
      return (
        <ol key={key} className="space-y-1.5 my-2.5 pl-1">
          {block.items.map((item, iIdx) => {
            const num = block.start + iIdx
            return (
              <li key={iIdx} className="flex items-start gap-2.5 text-xs sm:text-sm text-slate-200">
                <span className="font-mono text-[11px] font-semibold text-teal-400 bg-teal-500/10 px-1.5 py-0.5 rounded border border-teal-500/20 shrink-0 mt-0.5">
                  {num}
                </span>
                <div className="flex-1 min-w-0">
                  {renderInline(item, citations, onSelectCitation)}
                </div>
              </li>
            )
          })}
        </ol>
      )
    }

    case 'paragraph': {
      return (
        <p key={key} className="text-xs sm:text-sm text-slate-200 leading-relaxed my-2">
          {renderInline(block.text, citations, onSelectCitation)}
        </p>
      )
    }

    default:
      return null
  }
}

// ── Code Block Container with Copy Button ────────────────────────────────────

const CodeBlockContainer: React.FC<{ language: string; code: string }> = ({
  language,
  code,
}) => {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 rounded-xl bg-slate-950/90 border border-slate-800 overflow-hidden shadow-inner text-xs font-mono">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/80 border-b border-slate-800/80 text-[11px] text-slate-400">
        <span className="uppercase tracking-wider font-semibold text-teal-400/90">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 transition-colors p-1 rounded hover:bg-slate-800 cursor-pointer"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-teal-400" />
              <span className="text-teal-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="overflow-x-auto p-3.5">
        <pre className="text-teal-300 leading-relaxed whitespace-pre font-mono">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  )
}

// ── Inline Formatter (Bold, Italic, Code, Links, Citations) ─────────────────

function renderInline(
  text: string,
  citations: Citation[],
  onSelectCitation?: (id: string, citations: Citation[]) => void
): React.ReactNode {
  if (!text) return null

  // Pattern matches:
  // 1. Citation badges: [Source 1], [Source1], [Source 2], [1], [2]
  // 2. Markdown Links: [link text](url)
  // 3. Inline code: `code`
  // 4. Bold: **text**
  // 5. Italic: *text* or _text_
  // 6. Strikethrough: ~~text~~
  const tokenRegex =
    /(\[Source\s*\d+\]|\[\d+\]|\[[^\]]+\]\([^\)]+\)|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|~~[^~]+~~)/g

  const parts = text.split(tokenRegex)

  return parts.map((part, idx) => {
    if (!part) return null

    // 1. Citation token e.g. [Source 1] or [Source1] or [1]
    const sourceMatch = part.match(/^\[Source\s*(\d+)\]$/i) || part.match(/^\[(\d+)\]$/)
    if (sourceMatch) {
      const sourceNum = parseInt(sourceMatch[1], 10)
      const matchedCitation = citations[sourceNum - 1]
      const citationId = matchedCitation?.id || `source-${sourceNum}`
      const title = matchedCitation?.documentName || `Source ${sourceNum}`

      return (
        <button
          key={idx}
          type="button"
          onClick={() => {
            if (onSelectCitation) {
              onSelectCitation(citationId, citations)
            }
          }}
          className="inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.5 rounded-md bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 hover:border-teal-400 text-[11px] font-mono font-medium transition-all cursor-pointer shadow-xs group align-baseline"
          title={title}
          aria-label={`View citation for ${title}`}
        >
          <FileText className="w-2.5 h-2.5 text-teal-400 group-hover:scale-110 transition-transform" />
          <span>[{sourceNum}]</span>
        </button>
      )
    }

    // 2. Markdown link: [text](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (linkMatch) {
      const linkText = linkMatch[1]
      const linkUrl = linkMatch[2]
      return (
        <a
          key={idx}
          href={linkUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-teal-400 hover:text-teal-300 underline underline-offset-2 decoration-teal-500/40 hover:decoration-teal-400 transition-colors inline-flex items-center gap-0.5 mx-0.5 font-medium"
        >
          <span>{linkText}</span>
          <ExternalLink className="w-3 h-3 inline-block" />
        </a>
      )
    }

    // 3. Inline code: `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 mx-0.5 rounded-md bg-slate-800 text-teal-300 font-mono text-[11px] sm:text-xs border border-slate-700/70 shadow-xs"
        >
          {part.slice(1, -1)}
        </code>
      )
    }

    // 4. Bold: **text**
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-slate-100">
          {renderInline(part.slice(2, -2), citations, onSelectCitation)}
        </strong>
      )
    }

    // 5. Strikethrough: ~~text~~
    if (part.startsWith('~~') && part.endsWith('~~') && part.length >= 4) {
      return (
        <del key={idx} className="line-through text-slate-400">
          {renderInline(part.slice(2, -2), citations, onSelectCitation)}
        </del>
      )
    }

    // 6. Italic: *text*
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return (
        <em key={idx} className="italic text-slate-200">
          {renderInline(part.slice(1, -1), citations, onSelectCitation)}
        </em>
      )
    }

    // Plain text segment
    return <span key={idx}>{part}</span>
  })
}
