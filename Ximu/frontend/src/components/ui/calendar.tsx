import * as React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const DAYS = ['日', '一', '二', '三', '四', '五', '六'];

interface CalendarProps {
  value?: Date | null;
  onChange?: (date: Date | null) => void;
  className?: string;
}

export function Calendar({ value, onChange, className }: CalendarProps) {
  const today = new Date();
  const [viewDate, setViewDate] = React.useState(value ? new Date(value) : today);

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const cells: Array<{ day: number; current: boolean; date: Date }> = [];

  // Previous month trailing days
  for (let i = firstDay - 1; i >= 0; i--) {
    const d = daysInPrevMonth - i;
    cells.push({
      day: d,
      current: false,
      date: new Date(year, month - 1, d),
    });
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({
      day: d,
      current: true,
      date: new Date(year, month, d),
    });
  }

  // Next month leading days to fill 6 rows (42 cells)
  const remaining = 42 - cells.length;
  for (let d = 1; d <= remaining; d++) {
    cells.push({
      day: d,
      current: false,
      date: new Date(year, month + 1, d),
    });
  }

  const prevMonth = () => setViewDate(new Date(year, month - 1, 1));
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1));
  const prevYear = () => setViewDate(new Date(year - 1, month, 1));
  const nextYear = () => setViewDate(new Date(year + 1, month, 1));

  const isToday = (d: Date) =>
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate();

  const isSelected = (d: Date) =>
    value &&
    d.getFullYear() === value.getFullYear() &&
    d.getMonth() === value.getMonth() &&
    d.getDate() === value.getDate();

  return (
    <div className={cn('w-64 select-none', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={prevYear}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={prevMonth}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>
        <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
          {year}年{month + 1}月
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={nextMonth}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={nextYear}
            className="rounded p-0.5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {DAYS.map((d) => (
          <div key={d} className="h-7 text-center text-[10px] text-muted-foreground leading-7">
            {d}
          </div>
        ))}
      </div>

      {/* Day grid */}
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((cell, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onChange && onChange(cell.date)}
            className={cn(
              'h-7 w-7 mx-auto rounded-full text-xs transition-colors flex items-center justify-center',
              cell.current
                ? 'text-foreground hover:bg-accent'
                : 'text-muted-foreground hover:bg-muted',
              isSelected(cell.date) && 'bg-pink-500 text-white hover:bg-pink-600',
              !isSelected(cell.date) && isToday(cell.date) && 'ring-1 ring-pink-400',
            )}
          >
            {cell.day}
          </button>
        ))}
      </div>
    </div>
  );
}
