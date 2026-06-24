import { useState } from 'react';
import { Palette, Type, Space, ChevronDown, ChevronRight, RotateCcw, LayoutGrid, Sparkles } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';
import { Label } from '@/components/ui/label';
import { useResumeStore } from '@/stores/resume-store';
import type { ThemeConfig } from '@/types/resume';
import { TEMPLATES, TEMPLATE_NAMES } from '@/lib/constants';
import { TemplateThumbnail } from '../template/TemplateThumbnail';

const DEFAULT_THEME: ThemeConfig = {
  primaryColor: '#1a1a1a',
  accentColor: '#3b82f6',
  fontFamily: 'Inter',
  fontSize: 'medium',
  lineSpacing: 1.5,
  margin: { top: 20, right: 20, bottom: 20, left: 20 },
  sectionSpacing: 16,
};

const PRESET_THEMES = [
  { id: 'classic', colors: ['#1a1a1a', '#3b82f6', '#ffffff', '#374151'], config: { primaryColor: '#1a1a1a', accentColor: '#3b82f6', fontFamily: 'Georgia', fontSize: 'medium' as const, lineSpacing: 1.5, margin: { top: 24, right: 24, bottom: 24, left: 24 }, sectionSpacing: 16 } },
  { id: 'modern', colors: ['#0f172a', '#6366f1', '#f8fafc', '#475569'], config: { primaryColor: '#0f172a', accentColor: '#6366f1', fontFamily: 'Inter', fontSize: 'medium' as const, lineSpacing: 1.6, margin: { top: 20, right: 20, bottom: 20, left: 20 }, sectionSpacing: 14 } },
  { id: 'minimal', colors: ['#27272a', '#a1a1aa', '#ffffff', '#52525b'], config: { primaryColor: '#27272a', accentColor: '#a1a1aa', fontFamily: 'Helvetica', fontSize: 'small' as const, lineSpacing: 1.4, margin: { top: 28, right: 28, bottom: 28, left: 28 }, sectionSpacing: 12 } },
  { id: 'elegant', colors: ['#1c1917', '#b45309', '#fffbeb', '#57534e'], config: { primaryColor: '#1c1917', accentColor: '#b45309', fontFamily: 'Palatino', fontSize: 'medium' as const, lineSpacing: 1.6, margin: { top: 26, right: 26, bottom: 26, left: 26 }, sectionSpacing: 18 } },
  { id: 'bold', colors: ['#020617', '#e11d48', '#fff1f2', '#334155'], config: { primaryColor: '#020617', accentColor: '#e11d48', fontFamily: 'Arial', fontSize: 'large' as const, lineSpacing: 1.5, margin: { top: 20, right: 20, bottom: 20, left: 20 }, sectionSpacing: 16 } },
  { id: 'creative', colors: ['#134e4a', '#0d9488', '#f0fdfa', '#115e59'], config: { primaryColor: '#134e4a', accentColor: '#0d9488', fontFamily: 'Verdana', fontSize: 'medium' as const, lineSpacing: 1.5, margin: { top: 22, right: 22, bottom: 22, left: 22 }, sectionSpacing: 14 } },
];

const FONT_OPTIONS = ['Inter', 'Georgia', 'Helvetica', 'Arial', 'Palatino', 'Verdana'];

function CollapsibleSection({ title, icon: Icon, children, defaultOpen = true }: { title: string; icon: React.ElementType; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full cursor-pointer items-center gap-2 py-2 text-left text-xs font-semibold uppercase tracking-wider text-zinc-400 transition-colors hover:text-zinc-600 dark:hover:text-zinc-300">
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <Icon className="h-3.5 w-3.5" />
        <span>{title}</span>
      </button>
      {open && <div className="space-y-3 pb-3 pl-5">{children}</div>}
    </div>
  );
}

export function ThemeEditor() {
  const { currentResume } = useResumeStore();
  const { setThemeConfig } = useResumeStore();
  const themeConfig: ThemeConfig = { ...DEFAULT_THEME, ...(currentResume?.themeConfig || {}) };
  const updateTheme = (updates: Partial<ThemeConfig>) => {
    if (!currentResume) return;
    setThemeConfig(updates);
  };

  return (
    <div className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-background">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Palette className="h-4 w-4 text-muted-foreground" />
          主题编辑
        </h3>
        <button type="button" onClick={() => updateTheme(DEFAULT_THEME)} className="cursor-pointer rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent">
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>
      <ScrollArea className="flex-1 min-h-0">
        <div className="px-4 py-3 space-y-1">
          <CollapsibleSection title="切换模板" icon={LayoutGrid} defaultOpen={false}>
            <div className="h-48 overflow-y-auto">
              <div className="grid grid-cols-3 gap-2">
                {TEMPLATES.map((tpl) => (
                  <button
                    key={tpl}
                    type="button"
                    className={`group/tpl cursor-pointer overflow-hidden rounded-lg border-2 transition-all ${currentResume?.template === tpl ? 'border-pink-500 shadow-sm' : 'border-border hover:border-muted-foreground'}`}
                    onClick={() => useResumeStore.getState().setTemplate(tpl)}
                  >
                    <div className="bg-background p-1">
                      <TemplateThumbnail template={tpl} className="mx-auto h-[56px] w-[40px] shadow-sm ring-1 ring-zinc-200/50" />
                    </div>
                    <div className={`truncate px-1 py-0.5 text-center text-[10px] font-medium ${currentResume?.template === tpl ? 'bg-pink-50 text-pink-700' : 'text-zinc-500'}`}>{TEMPLATE_NAMES[tpl] ?? tpl}</div>
                  </button>
                ))}
              </div>
            </div>
          </CollapsibleSection>
          <Separator className="my-2 bg-muted-foreground/20" />
          <CollapsibleSection title="预设主题" icon={Sparkles as React.ElementType}>
            <div className="grid grid-cols-3 gap-2">
              {PRESET_THEMES.map((preset) => (
                <button key={preset.id} type="button" onClick={() => updateTheme(preset.config)} className="group flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border border-border">
                  <div className="flex gap-0.5">{preset.colors.map((color) => <div key={color} className="h-3 w-3 rounded-full border border-border" style={{ backgroundColor: color }} />)}</div>
                  <span className="text-[10px] text-zinc-500 group-hover:text-zinc-700 dark:group-hover:text-zinc-200">{preset.id === 'classic' ? '经典' : preset.id === 'modern' ? '现代' : preset.id === 'minimal' ? '简约' : preset.id === 'elegant' ? '优雅' : preset.id === 'bold' ? '大胆' : '创意'}</span>
                </button>
              ))}
            </div>
          </CollapsibleSection>
          <Separator className="my-2 bg-muted-foreground/20" />
          <CollapsibleSection title="颜色" icon={Palette as React.ElementType}>
            <div className="space-y-2">
              <ColorPicker label="主色" value={themeConfig.primaryColor} onChange={(c) => updateTheme({ primaryColor: c })} />
              <ColorPicker label="强调色" value={themeConfig.accentColor} onChange={(c) => updateTheme({ accentColor: c })} />
            </div>
          </CollapsibleSection>
          <Separator className="my-2 bg-muted-foreground/20" />
          <CollapsibleSection title="排版" icon={Type as React.ElementType}>
            <label className="block text-xs text-zinc-500">字体
              <select
                value={themeConfig.fontFamily}
                onChange={(e) => updateTheme({ fontFamily: e.target.value })}
                className="mt-1 w-full cursor-pointer rounded border-border bg-background text-foreground"
              >
                {FONT_OPTIONS.map((f) => <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>)}
              </select>
            </label>
            <label className="block text-xs text-zinc-500">字号</label>
            <div className="mt-1.5 grid grid-cols-3 gap-1.5">
              {[
                { value: 'small', label: '小' },
                { value: 'medium', label: '中' },
                { value: 'large', label: '大' },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => updateTheme({ fontSize: opt.value })}
                  className={`rounded border px-1.5 py-px text-[10px] font-medium transition-all ${
                    themeConfig.fontSize === opt.value
                      ? 'border-pink-500 bg-pink-50 text-pink-600 dark:bg-pink-500/20 dark:text-pink-400'
                      : 'border-border text-muted-foreground hover:border-muted-foreground'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <label className="block text-xs text-zinc-500">行距
              <input type="range" min={1.0} max={2.5} step={0.1} value={themeConfig.lineSpacing} onChange={(e) => updateTheme({ lineSpacing: Number(e.target.value) })} className="mt-1 w-full" />
              <span className="text-xs text-zinc-400">{themeConfig.lineSpacing.toFixed(1)}</span>
            </label>
          </CollapsibleSection>
          <Separator className="my-2 bg-muted-foreground/20" />
          <CollapsibleSection title="间距" icon={Space as React.ElementType}>
            <label className="block text-xs text-zinc-500">区块间距
              <input type="range" min={4} max={32} step={2} value={themeConfig.sectionSpacing} onChange={(e) => updateTheme({ sectionSpacing: Number(e.target.value) })} className="mt-1 w-full" />
              <span className="text-xs text-zinc-400">{themeConfig.sectionSpacing}px</span>
            </label>
            <div className="mt-1.5 space-y-2">
              <span className="text-xs text-zinc-500">页边距</span>
              <div className="grid grid-cols-4 gap-1">
                {(['top', 'right', 'bottom', 'left'] as const).map((dir) => (
                  <div key={dir} className="flex flex-col items-center">
                    <span className="mb-1 text-[9px] text-zinc-400">{dir === 'top' ? '上' : dir === 'right' ? '右' : dir === 'bottom' ? '下' : '左'}</span>
                    <input
                      type="number"
                      min={0}
                      max={50}
                      value={themeConfig.margin[dir]}
                      onChange={(e) => updateTheme({ margin: { ...themeConfig.margin, [dir]: Number(e.target.value) } })}
                      className="w-full rounded border-border bg-background text-foreground"
                    />
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleSection>
        </div>
      </ScrollArea>
    </div>
  );
}

function ColorPicker({ label, value, onChange }: { label: string; value: string; onChange: (c: string) => void }) {
  return (
    <div className="flex items-center justify-between">
      <Label className="text-xs text-zinc-600 dark:text-zinc-400">{label}</Label>
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className="flex cursor-pointer items-center gap-2 rounded-md border-border bg-background text-foreground"
          >
            <div className="h-4 w-4 rounded-sm border border-border" style={{ backgroundColor: value }} />
            <span className="font-mono text-zinc-500">{value}</span>
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-56 p-2 bg-popover shadow-lg border border-input" align="end">
          <div className="relative h-6 w-full border border-border overflow-hidden">
            <div
              className="absolute inset-0"
              style={{ backgroundColor: value }}
            />
            <input
              type="color"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
            />
          </div>
          <div className="h-2" />
          <input
            type="text"
            value={value}
            onChange={(e) => {
              const v = e.target.value;
              if (/^#[0-9a-fA-F]{0,6}$/.test(v)) {
                onChange(v);
              }
            }}
            placeholder="#000000"
            className="h-8 w-full rounded border-border bg-background text-foreground"
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
