import type { SectionComponentProps } from './helpers';
import { TA, c } from './helpers';

export function Summary({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  return (
    <TA
      label="个人简介"
      value={d.text || ''}
      onChange={(e) => onUpdate({ text: e.target.value })}
      rows={4}
      placeholder="写一段个人简介..."
    />
  );
}
