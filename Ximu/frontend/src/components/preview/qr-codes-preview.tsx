
import type { QrCodeItem } from '../../types/resume';

interface QrCodesPreviewProps {
  items: QrCodeItem[];
}

function isValidUrl(str: string): boolean {
  if (!str.trim()) return false;
  try {
    const raw = str.startsWith('http') ? str : `https://${str}`;
    const url = new URL(raw);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return false;
    const host = url.hostname;
    return host === 'localhost' || /\.\w{2,}$/.test(host) || /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
  } catch {
    return false;
  }
}

export function QrCodesPreview({ items }: QrCodesPreviewProps) {
  const filtered = items.filter((q) => isValidUrl(q.url));

  // Placeholder: QR code generation requires a library (qrcode or similar).
  // For now, show a placeholder with the URL label.
  if (filtered.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '16px 24px', paddingTop: '4px' }}>
      {filtered.map((qr) => (
        <div key={qr.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', width: 96 }}>
          <div style={{
            width: 80,
            height: 80,
            backgroundColor: '#f3f4f6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
            fontSize: '10px',
            color: '#9ca3af',
          }}>
            QR
          </div>
          {qr.label && (
            <span style={{ fontSize: '10px', color: '#6b7280', lineHeight: 1.2, textAlign: 'center', wordBreak: 'break-all', maxWidth: 96 }}>{qr.label}</span>
          )}
        </div>
      ))}
    </div>
  );
}
