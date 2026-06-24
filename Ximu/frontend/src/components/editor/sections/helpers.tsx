import { useEffect, useRef, useState, type ComponentProps } from 'react';
import { ChevronLeft, ChevronRight, CalendarDays, X, Plus } from 'lucide-react';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';

const CURRENT_YEAR = new Date().getFullYear();
const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

export const YearMonthPicker = ({
  label,
  value = '',
  onChange,
}: {
  label: string;
  value?: string;
  onChange: (v: string) => void;
}) => {
  const parse = (): [number, number] => {
    if (!value) return [CURRENT_YEAR, 0];
    const parts = value.split('.');
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1] || '1', 10) - 1;
    return [isNaN(y) ? CURRENT_YEAR : y, isNaN(m) ? 0 : m];
  };
  const [selYear, selMonth] = parse();
  const [pickerYear, setPickerYear] = useState(selYear);
  const [open, setOpen] = useState(false);
  const display = value || '选择日期';

  const prevYear = () => setPickerYear((y) => y - 1);
  const nextYear = () => setPickerYear((y) => y + 1);

  const handleSelect = (m: number) => {
    onChange(`${pickerYear}.${String(m + 1).padStart(2, '0')}`);
    setOpen(false);
  };

  return (
    <label className="block">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="mt-1 flex w-full items-center justify-between rounded border border-input bg-muted px-2.5 py-1.5 text-sm text-foreground transition-colors hover:border-foreground/30 focus:border-pink-300 focus:outline-none"
          >
            <span className={!value ? 'text-muted-foreground' : ''}>{display}</span>
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-auto border border-input bg-card p-3" align="start" sideOffset={8}>
          {/* Year nav */}
          <div className="flex items-center justify-between mb-3">
            <button type="button" onClick={prevYear} className="rounded p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-medium text-foreground">{pickerYear}年</span>
            <button type="button" onClick={nextYear} className="rounded p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
          {/* 12-month grid */}
          <div className="grid grid-cols-4 gap-1.5">
            {MONTH_LABELS.map((label, i) => {
              const isSelected = pickerYear === selYear && i === selMonth;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSelect(i)}
                  className={cn(
                    'h-8 rounded-lg text-xs font-medium transition-colors',
                    isSelected
                      ? 'bg-pink-500 text-white hover:bg-pink-600'
                      : 'bg-muted text-muted-foreground hover:bg-accent',
                  )}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </PopoverContent>
      </Popover>
    </label>
  );
};

export const F = ({ label, ...props }: { label: string } & Omit<ComponentProps<'input'>, 'ref'>) => (
  <label className="block">
    <span className="text-xs font-medium text-muted-foreground">{label}</span>
    <input className="mt-1 w-full rounded border border-input bg-background h-8 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-pink-300 focus:outline-none px-2.5" {...props} />
  </label>
);

function AutoResizeTextarea(props: Omit<ComponentProps<'textarea'>, 'ref'>) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  });

  return (
    <textarea
      ref={ref}
      rows={1}
      className="mt-1 w-full rounded border border-input bg-background text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-pink-300 focus:outline-none resize-none overflow-hidden px-2.5 py-2 min-h-[2.5rem]"
      {...props}
    />
  );
}

export const TA = ({ label, ...props }: { label: string } & Omit<ComponentProps<'textarea'>, 'ref'>) => (
  <label className="block">
    <span className="text-xs font-medium text-muted-foreground">{label}</span>
    <AutoResizeTextarea {...props} />
  </label>
);

export const c = (section: { content: unknown }) => section.content as any;

export type SectionComponentProps = {
  section: { content: unknown };
  onUpdate: (content: Record<string, unknown>) => void;
};

export function addItemState<T extends { id: string }>(items: T[], newItem: T): T[] {
  return [...items, newItem];
}

export function makeId(): string {
  return crypto.randomUUID?.() || Math.random().toString(36).slice(2);
}

export function FieldWrapper({ children, columns = 2 }: { children: React.ReactNode; columns?: number }) {
  return (
    <div
      className="grid gap-3"
      style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
    >
      {children}
    </div>
  );
}

export const S = ({ label, value, options, onChange, placeholder }: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  placeholder?: string;
}) => {
  const id = `select-${label}`;
  return (
    <div>
      <span id={id} className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</span>
      <Select value={value || ''} onValueChange={onChange} aria-labelledby={id}>
        <SelectTrigger className="mt-1 border border-input bg-background text-foreground h-8" aria-labelledby={id}>
          <SelectValue placeholder={placeholder || '请选择'} />
        </SelectTrigger>
        <SelectContent className="border-input bg-card text-foreground">
          {options.map((opt) => (
            <SelectItem key={opt} value={opt} className="text-foreground focus:bg-muted focus:text-foreground">
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};

export function EditableList({ label, items, onChange, placeholder }: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
}) {
  const updateItem = (index: number, value: string) => {
    const updated = [...items];
    updated[index] = value;
    onChange(updated);
  };

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="space-y-1.5">
        {items.map((item, index) => (
          <div key={index} className="flex items-center gap-1">
            <input
              type="text"
              value={item}
              onChange={(e) => updateItem(index, e.target.value)}
              placeholder={placeholder}
              className="flex-1 rounded border border-input bg-background h-8 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-pink-300 focus:outline-none px-2.5"
            />
            <button
              type="button"
              onClick={() => removeItem(index)}
              className="h-8 w-8 shrink-0 rounded text-zinc-400 hover:bg-accent hover:text-red-500 transition-colors flex items-center justify-center cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange([...items, ''])}
          className="h-7 cursor-pointer gap-1 text-xs"
        >
          <Plus className="h-3 w-3" />添加
        </Button>
      </div>
    </div>
  );
}

export function TagInput({ label, tags, onChange, placeholder }: {
  label: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}) {
  const addItem = () => onChange([...(tags || []), '']);

  const updateItem = (index: number, value: string) => {
    const updated = [...(tags || [])];
    updated[index] = value;
    onChange(updated);
  };

  const removeItem = (index: number) => {
    onChange((tags || []).filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <div className="space-y-1.5">
        {(tags || []).map((tag, index) => (
          <div key={index} className="flex items-center gap-1">
            <input
              type="text"
              value={tag}
              onChange={(e) => updateItem(index, e.target.value)}
              placeholder={placeholder}
              className="flex-1 rounded border border-input bg-background h-8 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:border-pink-300 focus:outline-none px-2.5"
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => removeItem(index)}
              className="h-8 w-8 shrink-0 cursor-pointer p-0 text-zinc-400 hover:text-red-500"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={addItem}
          className="h-7 cursor-pointer gap-1 text-xs"
        >
          <Plus className="h-3 w-3" />添加
        </Button>
      </div>
    </div>
  );
}
