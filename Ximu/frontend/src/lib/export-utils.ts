function sanitizeHtmlForPdf(html: string): string {
  return html
    .replace(/\s+shadow-(sm|md|lg|xl|2xl|xs|inner)\b/g, '')
    .replace(/\s+shadow-pink-500\/10\b/g, '')
    .replace(/style="([^"]*)box-shadow:[^;"]*;?([^"]*)"/gi, 'style="$1$2"')
    .replace(/style="([^"]*)filter:[^;"]*;?([^"]*)"/gi, 'style="$1$2"');
}

function markPdfItems(el: HTMLElement): void {
  el.querySelectorAll('[data-section]').forEach((section) => {
    const containers = Array.from(section.querySelectorAll('div')).filter((div) => {
      const childDivs = Array.from(div.children).filter((c) => c.tagName === 'DIV');
      return childDivs.length >= 2;
    });

    containers.forEach((container) => {
      Array.from(container.children).forEach((child) => {
        if (child instanceof HTMLElement && child.tagName === 'DIV') {
          child.setAttribute('data-pdf-item', '');
        }
      });
    });
  });
}

export function extractPreviewHtml(): string {
  const scopeEl = document.querySelector('[data-theme-scope]');
  if (!scopeEl) {
    return '';
  }

  const clone = scopeEl.cloneNode(true) as HTMLElement;
  markPdfItems(clone);

  const styleTags = document.querySelectorAll('style');
  let collectedStyles = '';
  styleTags.forEach((tag) => {
    collectedStyles += tag.innerHTML + '\n';
  });

  const scopeHtml = sanitizeHtmlForPdf(clone.outerHTML);

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { margin: 0; }
    ${collectedStyles}
  </style>
  <style>
    html, body, [data-theme-scope], [data-theme-scope] *,
    [data-theme-scope] *::before, [data-theme-scope] *::after {
      box-shadow: none !important;
      filter: none !important;
      text-shadow: none !important;
    }
    .shadow-xs, .shadow-sm, .shadow-md, .shadow-lg, .shadow-xl, .shadow-2xl, .shadow-inner {
      box-shadow: none !important;
    }
    @media print {
      @page {
        margin-top: 12mm;
        margin-bottom: 12mm;
      }
      @page :first {
        margin-top: 0;
      }
      [data-pdf-item] {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      [data-section] h2,
      [data-section] h3 {
        break-after: avoid;
        page-break-after: avoid;
        orphans: 3;
        widows: 3;
      }
    }
  </style>
</head>
<body>
  <div class="bg-white" style="width: 794px; margin: 0 auto;">
    ${scopeHtml}
  </div>
</body>
</html>`;

  return html;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadJson(data: object, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  downloadBlob(blob, filename);
}

export function downloadText(text: string, filename: string): void {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  downloadBlob(blob, filename);
}

export function downloadHtml(html: string, filename: string): void {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  downloadBlob(blob, filename);
}
