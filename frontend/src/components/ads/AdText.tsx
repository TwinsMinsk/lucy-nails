import { Fragment, type ReactNode } from "react"

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|https?:\/\/[^\s)]+)/g

/** Inline marks the campaign texts use: **bold**, `code` and bare links. No HTML is rendered. */
export function InlineText({ text }: { text: string }) {
    return (
        <>
            {text.split(INLINE).map((part, index) => {
                if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
                    return <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong>
                }
                if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
                    return <code key={index} className="rounded bg-muted px-1 py-0.5 text-[0.85em] break-all">{part.slice(1, -1)}</code>
                }
                if (/^https?:\/\//.test(part)) {
                    return <a key={index} href={part} target="_blank" rel="noreferrer" className="break-all text-primary underline underline-offset-2">{part}</a>
                }
                return <Fragment key={index}>{part}</Fragment>
            })}
        </>
    )
}

const ITEM = /^(- |\d+\. )/

/** Paragraphs, "- " and "1. " lists (indented lines continue an item) and "| a | b |" tables. */
export function RichText({ text }: { text: string }) {
    const blocks: ReactNode[] = []
    const lines = text.replace(/\r/g, "").split("\n")
    let index = 0
    while (index < lines.length) {
        const line = lines[index].trim()
        if (!line) {
            index += 1
            continue
        }
        const marker = line.match(ITEM)
        if (marker) {
            const ordered = marker[1] !== "- "
            const items: string[] = []
            while (index < lines.length) {
                const current = lines[index]
                const item = current.trim().match(ITEM)
                if (item && /^\d/.test(item[1]) === ordered) items.push(current.trim().slice(item[1].length))
                else if (items.length && /^\s+\S/.test(current) && !item) items[items.length - 1] += ` ${current.trim()}`
                else break
                index += 1
            }
            const List = ordered ? "ol" : "ul"
            blocks.push(
                <List key={blocks.length} className={`${ordered ? "list-decimal" : "list-disc"} space-y-1.5 pl-5`}>
                    {items.map((item, i) => <li key={i}><InlineText text={item} /></li>)}
                </List>,
            )
            continue
        }
        if (line.startsWith("|")) {
            const rows: string[][] = []
            while (index < lines.length && lines[index].trim().startsWith("|")) {
                const cells = lines[index].trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim())
                if (!cells.every((cell) => /^:?-+:?$/.test(cell))) rows.push(cells)
                index += 1
            }
            const [head, ...body] = rows
            blocks.push(
                <div key={blocks.length} className="overflow-x-auto">
                    <table className="w-full min-w-[32rem] text-sm">
                        <thead><tr className="border-b text-left text-muted-foreground">{head.map((cell, i) => <th key={i} className="p-2 font-medium">{cell}</th>)}</tr></thead>
                        <tbody>{body.map((row, r) => (
                            <tr key={r} className="border-b align-top last:border-0">{row.map((cell, c) => <td key={c} className="p-2"><InlineText text={cell} /></td>)}</tr>
                        ))}</tbody>
                    </table>
                </div>,
            )
            continue
        }
        const paragraph: string[] = []
        while (index < lines.length && lines[index].trim() && !ITEM.test(lines[index].trim()) && !lines[index].trim().startsWith("|")) {
            paragraph.push(lines[index].trim())
            index += 1
        }
        blocks.push(<p key={blocks.length}><InlineText text={paragraph.join(" ")} /></p>)
    }
    return <div className="space-y-3 leading-relaxed">{blocks}</div>
}
