import { Clock, FileText, FilePen, Star } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { WorkTask } from '../../types/work';

interface MessageListProps {
  tasks: WorkTask[];
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '未知';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins} 分钟前`;
  if (diffHours < 24) return `${diffHours} 小时前`;
  if (diffDays < 7) return `${diffDays} 天前`;
  return date.toLocaleDateString('zh-CN');
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '处理中',
    success: '已完成',
    error: '错误',
  };
  return map[status] || status;
}

function getStatusBadgeBg(status: string): string {
  const map: Record<string, string> = {
    pending: 'border-muted-foreground/50 bg-muted',
    running: 'border-amber-500/50 bg-amber-500/10',
    success: 'border-emerald-500/50 bg-emerald-500/10',
    error: 'border-red-500/50 bg-red-500/10',
  };
  return map[status] || 'border-muted-foreground/50 bg-muted';
}

function getStatusTextColor(status: string): string {
  const map: Record<string, string> = {
    pending: 'text-muted-foreground',
    running: 'text-amber-400',
    success: 'text-emerald-400',
    error: 'text-red-400',
  };
  return map[status] || 'text-muted-foreground';
}

function getStatusDot(status: string): string {
  const map: Record<string, string> = {
    pending: 'bg-muted-foreground',
    running: 'bg-amber-400 animate-pulse',
    success: 'bg-emerald-400',
    error: 'bg-red-400',
  };
  return map[status] || 'bg-muted-foreground';
}

function getTaskTypeTitle(taskType: string): string {
  const map: Record<string, string> = {
    parse: '解析任务',
    jd_generate: '子简历生成',
    jd_score: 'JD 评分',
  };
  return map[taskType] || '未知任务';
}

function getTaskTypeTitleStyle(taskType: string): string {
  const map: Record<string, string> = {
    parse: 'text-foreground',
    jd_generate: 'text-purple-400',
    jd_score: 'text-amber-400',
  };
  return map[taskType] || 'text-foreground';
}

function getTaskTypeIcon(taskType: string): LucideIcon {
  const map: Record<string, LucideIcon> = {
    parse: FileText,
    jd_generate: FilePen,
    jd_score: Star,
  };
  return map[taskType] || FileText;
}

function getTaskTypeColors(taskType: string): { bg: string; text: string } {
  const map: Record<string, { bg: string; text: string }> = {
    parse: { bg: 'bg-pink-500/10', text: 'text-pink-400' },
    jd_generate: { bg: 'bg-purple-500/10', text: 'text-purple-400' },
    jd_score: { bg: 'bg-amber-500/10', text: 'text-amber-400' },
  };
  return map[taskType] || map.parse;
}

export default function MessageList({ tasks }: MessageListProps) {
  return (
    <>
      <div className="px-4 py-3 border-b border-muted-foreground/20 flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">任务通知</h3>
        <span className="text-xs text-muted-foreground">{tasks.length} 个任务</span>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {tasks.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-8 text-gray-500">
            <FileText className="w-8 h-8" />
            <p className="text-sm">暂无任务</p>
          </div>
        )}

        {tasks.length > 0 && (
          <ul className="divide-y divide-muted-foreground/20">
            {tasks.map((task: WorkTask) => (
              <li key={task.id} className="px-4 py-3 hover:bg-muted transition-colors">
                <div className="flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg ${getTaskTypeColors(task.taskType).bg} flex items-center justify-center shrink-0`}>
                    {(() => {
                      const Icon = getTaskTypeIcon(task.taskType);
                      return <Icon className={`w-4 h-4 ${getTaskTypeColors(task.taskType).text}`} />;
                    })()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <p className={`text-sm truncate ${getTaskTypeTitleStyle(task.taskType)}`} title={getTaskTypeTitle(task.taskType)}>
                        {getTaskTypeTitle(task.taskType)}
                      </p>
                      <span className={`flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded border shrink-0 ${getStatusBadgeBg(task.status)}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${getStatusDot(task.status)}`} />
                        <span className={getStatusTextColor(task.status)}>
                          {getStatusLabel(task.status)}
                        </span>
                      </span>
                    </div>
                    {task.metaInfo?.fileName && (
                      <p className="text-xs text-muted-foreground truncate mb-1">{task.metaInfo.fileName}</p>
                    )}
                    {task.metaInfo?.title && (
                      <p className="text-xs text-muted-foreground truncate mb-1">{task.metaInfo.title}</p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-muted-foreground/60">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(task.createdAt)}</span>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
