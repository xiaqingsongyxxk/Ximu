import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { SectionComponentProps } from './helpers';
import { F, S, TA, c, makeId, YearMonthPicker, TagInput, EditableList } from './helpers';

const degreeOptions = ['初中', '高中', '中专', '大专', '本科', '学士', '硕士', '博士', '博士后'];

export function WorkExperience({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => {
    const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n });
  };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), company: '', position: '', location: '', startDate: '', endDate: '', current: false, description: '', technologies: [], highlights: [] }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <F label="公司名称" value={item.company || ''} onChange={(e) => updateItem(items.indexOf(item), 'company', e.target.value)} />
              <F label="职位" value={item.position || ''} onChange={(e) => updateItem(items.indexOf(item), 'position', e.target.value)} />
              <YearMonthPicker label="开始日期" value={item.startDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'startDate', v)} />
              <YearMonthPicker label="结束日期" value={item.endDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'endDate', v)} />
              <F label="地点" value={item.location || ''} onChange={(e) => updateItem(items.indexOf(item), 'location', e.target.value)} />
            </div>
            <TA label="描述" value={item.description || ''} onChange={(e) => updateItem(items.indexOf(item), 'description', e.target.value)} rows={2} />
            <TagInput label="技术栈" tags={item.technologies || []} onChange={(tags) => updateItem(items.indexOf(item), 'technologies', tags)} placeholder="输入技术后回车添加" />
            <TagInput label="亮点" tags={item.highlights || []} onChange={(tags) => updateItem(items.indexOf(item), 'highlights', tags)} placeholder="输入亮点后回车添加" />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加经历</Button>
    </div>
  );
}

export function Education({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => {
    const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n });
  };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), institution: '', degree: '', field: '', location: '', startDate: '', endDate: '', gpa: '', highlights: [] }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <F label="学校" value={item.institution || ''} onChange={(e) => updateItem(items.indexOf(item), 'institution', e.target.value)} />
              <F label="地点" value={item.location || ''} onChange={(e) => updateItem(items.indexOf(item), 'location', e.target.value)} />
              <S label="学位" value={item.degree || ''} options={degreeOptions} onChange={(v) => updateItem(items.indexOf(item), 'degree', v)} />
              <F label="GPA" value={item.gpa || ''} onChange={(e) => updateItem(items.indexOf(item), 'gpa', e.target.value)} />
              <F label="专业" value={item.field || ''} onChange={(e) => updateItem(items.indexOf(item), 'field', e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <YearMonthPicker label="入学时间" value={item.startDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'startDate', v)} />
              <YearMonthPicker label="毕业时间" value={item.endDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'endDate', v)} />
            </div>
            <TagInput label="亮点" tags={item.highlights || []} onChange={(tags) => updateItem(items.indexOf(item), 'highlights', tags)} placeholder="输入亮点后回车添加" />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加教育经历</Button>
    </div>
  );
}

export function Skills({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const categories: Array<{ id: string; name: string; skills: string[] }> = d.categories || [];
  const updateCategory = (idx: number, updates: any) => {
    const n = [...categories]; n[idx] = { ...n[idx], ...updates }; onUpdate({ categories: n });
  };
  const addCategory = () => onUpdate({ categories: [...categories, { id: makeId(), name: '', skills: [] }] });
  const removeCategory = (idx: number) => onUpdate({ categories: categories.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {categories.map((cat, index) => (
        <div key={cat.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <F label="分类名称" value={cat.name || ''} onChange={(e) => updateCategory(index, { name: e.target.value })} placeholder="输入分类名称" />
              <Button variant="ghost" size="sm" className="mt-5 h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeCategory(index)}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <EditableList label="技能" items={cat.skills} onChange={(skills) => updateCategory(index, { skills })} placeholder="输入技能后回车添加" />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addCategory} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加技能分类</Button>
    </div>
  );
}

export function Projects({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => { const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n }); };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), name: '', url: '', startDate: '', endDate: '', description: '', technologies: [], highlights: [] }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <F label="项目名称" value={item.name || ''} onChange={(e) => updateItem(items.indexOf(item), 'name', e.target.value)} />
              <F label="项目链接" value={item.url || ''} onChange={(e) => updateItem(items.indexOf(item), 'url', e.target.value)} />
              <YearMonthPicker label="开始时间" value={item.startDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'startDate', v)} />
              <YearMonthPicker label="结束时间" value={item.endDate || ''} onChange={(v) => updateItem(items.indexOf(item), 'endDate', v)} />
            </div>
            <TA label="描述" value={item.description || ''} onChange={(e) => updateItem(items.indexOf(item), 'description', e.target.value)} rows={2} />
            <TagInput label="技术栈" tags={item.technologies || []} onChange={(tags) => updateItem(items.indexOf(item), 'technologies', tags)} placeholder="输入技术后回车添加" />
            <TagInput label="亮点" tags={item.highlights || []} onChange={(tags) => updateItem(items.indexOf(item), 'highlights', tags)} placeholder="输入亮点后回车添加" />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加项目</Button>
    </div>
  );
}

export function Certifications({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => { const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n }); };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), name: '', issuer: '', date: '', description: '' }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <F label="名称" value={item.name || ''} onChange={(e) => updateItem(items.indexOf(item), 'name', e.target.value)} />
              <F label="颁发机构" value={item.issuer || ''} onChange={(e) => updateItem(items.indexOf(item), 'issuer', e.target.value)} />
              <YearMonthPicker label="日期" value={item.date || ''} onChange={(v) => updateItem(items.indexOf(item), 'date', v)} />
            </div>
            <TA label="描述" value={item.description || ''} onChange={(e) => updateItem(items.indexOf(item), 'description', e.target.value)} rows={2} />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加证书</Button>
    </div>
  );
}

export function Languages({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => { const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n }); };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), language: '', proficiency: '', description: '' }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <F label="语言" value={item.language || ''} onChange={(e) => updateItem(items.indexOf(item), 'language', e.target.value)} />
              <div className="flex items-end gap-1">
                <F label="水平" value={item.proficiency || ''} onChange={(e) => updateItem(items.indexOf(item), 'proficiency', e.target.value)} />
                <Button variant="ghost" size="sm" className="h-8 w-8 cursor-pointer p-0 text-zinc-400 hover:text-red-500" onClick={() => removeItem(index)}>
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            <TA label="描述" value={item.description || ''} onChange={(e) => updateItem(items.indexOf(item), 'description', e.target.value)} rows={2} />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加语言</Button>
    </div>
  );
}

export function GitHub({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: any[] = d.items || [];
  const updateItem = (idx: number, field: string, value: any) => { const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n }); };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), repoUrl: '', name: '', stars: 0, language: '', description: '' }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <F label="仓库名" value={item.name || ''} onChange={(e) => updateItem(items.indexOf(item), 'name', e.target.value)} />
            <F label="仓库地址" value={item.repoUrl || ''} onChange={(e) => updateItem(items.indexOf(item), 'repoUrl', e.target.value)} />
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加仓库</Button>
    </div>
  );
}

export function QrCodes({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const items: Array<{ id: string; label: string; url: string }> = d.items || [];
  const updateItem = (idx: number, field: string, value: string) => { const n = [...items]; n[idx] = { ...n[idx], [field]: value }; onUpdate({ items: n }); };
  const addItem = () => onUpdate({ items: [...items, { id: makeId(), label: '', url: '' }] });
  const removeItem = (idx: number) => onUpdate({ items: items.filter((_, i) => i !== idx) });

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={item.id}>
          {index > 0 && <Separator className="mb-4" />}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-zinc-400">#{index + 1}</span>
              <Button variant="ghost" size="sm" className="h-7 cursor-pointer p-1 text-zinc-400 hover:text-red-500" onClick={() => removeItem(items.indexOf(item))}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="grid grid-cols-1 gap-x-4 gap-y-2">
              <F label="标签" value={item.label} onChange={(e) => updateItem(items.indexOf(item), 'label', e.target.value)} />
              <F label="URL" value={item.url} onChange={(e) => updateItem(items.indexOf(item), 'url', e.target.value)} />
            </div>
          </div>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={addItem} className="w-full cursor-pointer gap-1"><Plus className="h-3.5 w-3.5" />添加二维码</Button>
    </div>
  );
}

export function CustomSection({ section, onUpdate }: SectionComponentProps) {
  const d = c(section);
  const updateField = (field: string, value: any) => onUpdate({ ...d, [field]: value });
  const resetFields = () => onUpdate({ id: makeId(), title: '', date: '', description: '' });

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          <F label="标题" value={d.title || ''} onChange={(e) => updateField('title', e.target.value)} />
          <YearMonthPicker label="日期" value={d.date || ''} onChange={(v) => updateField('date', v)} />
        </div>
        <TA label="描述" value={d.description || ''} onChange={(e) => updateField('description', e.target.value)} rows={2} />
      </div>
      <button type="button" onClick={resetFields} className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors">
        <span className="text-lg leading-none">+</span> 清空重置
      </button>
    </div>
  );
}
