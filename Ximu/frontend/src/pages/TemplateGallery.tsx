import { useState } from 'react';
import { X } from 'lucide-react';
import TemplateCard from '../components/template/TemplateCard';
import ResumePreview from '../components/preview/ResumePreview';
import { mockResume } from '../data/mockResume';
import { templateLabelsMap, TEMPLATE_ORDER } from '../lib/template-labels';

export default function TemplateGallery() {
  const [previewTemplate, setPreviewTemplate] = useState<string | null>(null);

  const handleUse = (templateId: string) => {
    alert(`已选择模板: ${templateLabelsMap[templateId]}`);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="shrink-0 mb-8">
        <h1 className="text-3xl font-bold text-foreground">模板</h1>
        <p className="text-sm text-muted-foreground mt-1">选择一个模板开始创建你的简历</p>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="flex justify-center">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {TEMPLATE_ORDER.map((id) => {
          const label = templateLabelsMap[id] || id;
          const previewResume = { ...mockResume, template: id };

          return (
            <TemplateCard
              key={id}
              templateId={id}
              templateName={label}
              resume={previewResume}
              onPreview={setPreviewTemplate}
              onUse={handleUse}
            />
          );
        })}
        </div>
        </div>
      </div>

      {previewTemplate && (
        <PreviewModal
          templateId={previewTemplate}
          onClose={() => setPreviewTemplate(null)}
          onUse={handleUse}
        />
      )}
    </div>
  );
}

function PreviewModal({ templateId, onClose, onUse }: { templateId: string; onClose: () => void; onUse: (id: string) => void }) {
  const previewResume = { ...mockResume, template: templateId };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative w-full max-w-4xl h-[90vh] flex flex-col bg-background rounded-xl border border-border overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-6">
            <h2 className="text-lg font-semibold text-foreground">
              预览：<span className="text-pink-400">{templateLabelsMap[templateId]}</span>
            </h2>
            <button
              onClick={() => onUse(templateId)}
              className="px-4 py-1.5 rounded-lg bg-[#e94560] text-primary-foreground hover:bg-[#d63653] transition-colors text-sm font-medium"
            >
              使用此模板
            </button>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-auto bg-card p-8">
          <div className="flex justify-center">
            <div className="w-[595px] border border-foreground/10 rounded-lg overflow-hidden">
              <ResumePreview resume={previewResume} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
