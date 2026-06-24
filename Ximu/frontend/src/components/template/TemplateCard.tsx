import type { Resume } from '../../types/resume';
import ResumePreview from '../preview/ResumePreview';
import { Eye } from 'lucide-react';

interface TemplateCardProps {
  templateId: string;
  templateName: string;
  resume: Resume;
  onPreview: (templateId: string) => void;
  onUse: (templateId: string) => void;
}

export default function TemplateCard({ templateId, templateName, resume, onPreview, onUse }: TemplateCardProps) {
  return (
    <div
      className="group flex flex-col rounded-2xl overflow-hidden bg-[#1a1a1a] border border-[#2a2a2e] transition-colors duration-200 hover:border-[#3a3a3e] hover:bg-[#1e1e1e]"
      style={{ width: '300px' }}
    >
      <div className="px-4 py-3 text-center">
        <h3 className="text-base font-bold text-white tracking-wide">{templateName}</h3>
      </div>

      <div className="relative overflow-hidden rounded-xl mx-2 mb-2" style={{ height: '340px' }}>
        <div
          className="absolute origin-top"
          style={{
            left: '50%',
            top: '0',
            width: '794px',
            transform: 'translateX(-50%) scale(0.30)',
          }}
        >
          <ResumePreview resume={resume} />
        </div>
      </div>

      <div className="flex gap-2.5 px-4 pb-4">
        <button
          onClick={() => onPreview(templateId)}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg cursor-pointer bg-transparent border border-[#555] text-white hover:bg-white/10 hover:text-white hover:border-white transition-all text-sm"
        >
          <Eye className="w-3.5 h-3.5" />
          <span>预览</span>
        </button>
        <button
          onClick={() => onUse(templateId)}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg cursor-pointer bg-[#ec4899] text-white hover:bg-[#db2777] font-medium transition-all text-sm"
        >
          使用此模板
        </button>
      </div>
    </div>
  );
}