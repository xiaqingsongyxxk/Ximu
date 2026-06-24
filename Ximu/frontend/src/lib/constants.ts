export const APP_NAME = 'Chiren';

export const SECTION_TYPES = [
  'personal_info',
  'summary',
  'work_experience',
  'education',
  'skills',
  'projects',
  'certifications',
  'languages',
  'github',
  'qr_codes',
  'custom',
] as const;

export type SectionType = (typeof SECTION_TYPES)[number];

export const DEFAULT_SECTION_TITLES: Record<string, string> = {
  personal_info: '个人信息',
  summary: '个人简介',
  work_experience: '工作经历',
  education: '教育背景',
  skills: '技能特长',
  projects: '项目经历',
  certifications: '证书&奖项',
  languages: '语言能力',
  github: 'GitHub',
  qr_codes: '二维码',
  custom: '自定义',
};

export const TEMPLATES = [
  'classic', 'modern', 'minimal', 'professional', 'two-column', 'creative', 'ats', 'academic', 'elegant', 'executive',
  'developer', 'designer', 'startup', 'formal', 'infographic', 'compact', 'euro', 'clean', 'bold', 'timeline',
  'nordic', 'corporate', 'consultant', 'finance', 'medical',
  'gradient', 'metro', 'material', 'coder', 'blocks',
  'magazine', 'artistic', 'retro', 'neon', 'watercolor',
  'swiss', 'japanese', 'berlin', 'luxe', 'rose',
  'architect', 'legal', 'teacher', 'scientist', 'engineer',
  'sidebar', 'card', 'zigzag', 'ribbon', 'mosaic',
] as const;
export type Template = (typeof TEMPLATES)[number];

export const TEMPLATE_NAMES: Record<string, string> = {
  classic: '经典',
  modern: '现代',
  minimal: '简约',
  professional: '专业',
  'two-column': '双栏',
  creative: '创意',
  ats: 'ATS',
  academic: '学术',
  elegant: '优雅',
  executive: '商务',
  developer: '开发者',
  designer: '设计师',
  startup: '创业',
  formal: '正式',
  infographic: '信息图',
  compact: '紧凑',
  euro: '欧式',
  clean: '清新',
  bold: '大胆',
  timeline: '时间线',
  nordic: '北欧',
  corporate: '企业',
  consultant: '咨询',
  finance: '金融',
  medical: '医疗',
  gradient: '渐变',
  metro: '地铁',
  material: '材质',
  coder: '程序员',
  blocks: '卡片',
  magazine: '杂志',
  artistic: '艺术',
  retro: '复古',
  neon: '霓虹',
  watercolor: '水彩',
  swiss: '瑞士',
  japanese: '日式',
  berlin: '柏林',
  luxe: '奢华',
  rose: '玫瑰',
  architect: '建筑',
  legal: '法律',
  teacher: '教师',
  scientist: '科学家',
  engineer: '工程师',
  sidebar: '侧边栏',
  card: '卡片',
  zigzag: '锯齿',
  ribbon: '丝带',
  mosaic: '马赛克',
};

export const BACKGROUND_TEMPLATES: ReadonlySet<string> = new Set([
  'modern', 'creative', 'two-column', 'executive', 'developer',
  'designer', 'startup', 'infographic', 'compact', 'bold',
  'corporate', 'finance', 'gradient', 'material', 'coder',
  'artistic', 'neon', 'berlin', 'engineer', 'sidebar', 'ribbon',
]);

export const TWO_COLUMN_TEMPLATES: Record<string, { bg: string; width: string }> = {
  'two-column': { bg: '#16213e', width: '35%' },
  sidebar:      { bg: '#1e40af', width: '35%' },
  coder:        { bg: '#0d1117', width: '32%' },
};

export const AUTOSAVE_DELAY = 500;
export const MAX_UNDO_STACK = 50;
