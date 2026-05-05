const ALLOWED_TAGS = new Set([
  "A",
  "B",
  "BLOCKQUOTE",
  "BR",
  "CODE",
  "EM",
  "H2",
  "H3",
  "H4",
  "I",
  "LI",
  "OL",
  "P",
  "PRE",
  "STRONG",
  "U",
  "UL",
]);

const ALLOWED_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);
const DROP_WITH_CONTENT = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED"]);

function isSafeHref(rawHref: string): boolean {
  try {
    const url = new URL(rawHref, window.location.origin);
    return ALLOWED_LINK_PROTOCOLS.has(url.protocol);
  } catch {
    return false;
  }
}

function sanitizeElement(element: ParentNode): void {
  for (const child of Array.from(element.children)) {
    if (DROP_WITH_CONTENT.has(child.tagName)) {
      child.remove();
      continue;
    }

    if (!ALLOWED_TAGS.has(child.tagName)) {
      sanitizeElement(child);
      child.replaceWith(...Array.from(child.childNodes));
      continue;
    }

    for (const attr of Array.from(child.attributes)) {
      const name = attr.name.toLowerCase();
      const value = attr.value;

      if (child.tagName === "A" && name === "href" && isSafeHref(value)) {
        child.setAttribute("rel", "noopener noreferrer");
        child.setAttribute("target", "_blank");
        continue;
      }

      if (child.tagName === "A" && (name === "title" || name === "target" || name === "rel")) {
        continue;
      }

      child.removeAttribute(attr.name);
    }

    sanitizeElement(child);
  }
}

export function sanitizeHtml(dirtyHtml: string): string {
  if (typeof window === "undefined") return "";

  const template = document.createElement("template");
  template.innerHTML = dirtyHtml;
  sanitizeElement(template.content);
  return template.innerHTML;
}
