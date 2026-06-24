import type { Resume } from '../types/resume';
import { AcademicTemplate } from '../components/preview/templates/academic';
import { ArchitectTemplate } from '../components/preview/templates/architect';
import { ArtisticTemplate } from '../components/preview/templates/artistic';
import { AtsTemplate } from '../components/preview/templates/ats';
import { BerlinTemplate } from '../components/preview/templates/berlin';
import { BlocksTemplate } from '../components/preview/templates/blocks';
import { BoldTemplate } from '../components/preview/templates/bold';
import { CardTemplate } from '../components/preview/templates/card';
import { ClassicTemplate } from '../components/preview/templates/classic';
import { CleanTemplate } from '../components/preview/templates/clean';
import { CoderTemplate } from '../components/preview/templates/coder';
import { CompactTemplate } from '../components/preview/templates/compact';
import { ConsultantTemplate } from '../components/preview/templates/consultant';
import { CorporateTemplate } from '../components/preview/templates/corporate';
import { CreativeTemplate } from '../components/preview/templates/creative';
import { DesignerTemplate } from '../components/preview/templates/designer';
import { DeveloperTemplate } from '../components/preview/templates/developer';
import { ElegantTemplate } from '../components/preview/templates/elegant';
import { EngineerTemplate } from '../components/preview/templates/engineer';
import { EuroTemplate } from '../components/preview/templates/euro';
import { ExecutiveTemplate } from '../components/preview/templates/executive';
import { FinanceTemplate } from '../components/preview/templates/finance';
import { FormalTemplate } from '../components/preview/templates/formal';
import { GradientTemplate } from '../components/preview/templates/gradient';
import { InfographicTemplate } from '../components/preview/templates/infographic';
import { JapaneseTemplate } from '../components/preview/templates/japanese';
import { LegalTemplate } from '../components/preview/templates/legal';
import { LuxeTemplate } from '../components/preview/templates/luxe';
import { MagazineTemplate } from '../components/preview/templates/magazine';
import { MaterialTemplate } from '../components/preview/templates/material';
import { MedicalTemplate } from '../components/preview/templates/medical';
import { MetroTemplate } from '../components/preview/templates/metro';
import { MinimalTemplate } from '../components/preview/templates/minimal';
import { ModernTemplate } from '../components/preview/templates/modern';
import { MosaicTemplate } from '../components/preview/templates/mosaic';
import { NeonTemplate } from '../components/preview/templates/neon';
import { NordicTemplate } from '../components/preview/templates/nordic';
import { ProfessionalTemplate } from '../components/preview/templates/professional';
import { RetroTemplate } from '../components/preview/templates/retro';
import { RibbonTemplate } from '../components/preview/templates/ribbon';
import { RoseTemplate } from '../components/preview/templates/rose';
import { ScientistTemplate } from '../components/preview/templates/scientist';
import { SidebarTemplate } from '../components/preview/templates/sidebar';
import { StartupTemplate } from '../components/preview/templates/startup';
import { SwissTemplate } from '../components/preview/templates/swiss';
import { TeacherTemplate } from '../components/preview/templates/teacher';
import { TimelineTemplate } from '../components/preview/templates/timeline';
import { TwoColumnTemplate } from '../components/preview/templates/two-column';
import { WatercolorTemplate } from '../components/preview/templates/watercolor';
import { ZigzagTemplate } from '../components/preview/templates/zigzag';

export const TEMPLATE_ORDER = [
  // 经典
  'classic',
  // 通用专业
  'professional', 'formal', 'elegant', 'corporate', 'ats', 'executive', 'consultant',
  // 现代极简
  'minimal', 'modern', 'clean', 'compact', 'swiss', 'nordic', 'gradient', 'bold',
  // 布局结构
  'two-column', 'sidebar', 'card', 'blocks', 'timeline', 'material',
  // 创意设计
  'creative', 'artistic', 'neon', 'watercolor', 'mosaic', 'luxe', 'retro', 'magazine', 'ribbon', 'rose', 'zigzag',
  // 行业定向
  'developer', 'coder', 'designer', 'architect', 'engineer', 'scientist', 'finance', 'medical', 'metro', 'legal', 'teacher', 'academic', 'startup',
  // 实验风格
  'japanese', 'euro', 'berlin', 'infographic',
];

export const templateLabelsMap: Record<string, string> = {
  academic: '学术',
  architect: '建筑师',
  artistic: '艺术',
  ats: 'ATS',
  berlin: '柏林',
  blocks: '模块',
  bold: '粗体',
  card: '卡片',
  classic: '经典',
  clean: '简洁',
  coder: '程序员',
  compact: '紧凑',
  consultant: '顾问',
  corporate: '企业',
  creative: '创意',
  designer: '设计师',
  developer: '开发者',
  elegant: '优雅',
  engineer: '工程师',
  euro: '欧洲',
  executive: '高管',
  finance: '金融',
  formal: '正式',
  gradient: '渐变',
  infographic: '信息图',
  japanese: '日式',
  legal: '法律',
  luxe: '奢华',
  magazine: '杂志',
  material: 'Material',
  medical: '医疗',
  metro: '地铁',
  minimal: '极简',
  modern: '现代',
  mosaic: '马赛克',
  neon: '霓虹',
  nordic: '北欧',
  professional: '专业',
  retro: '复古',
  ribbon: '缎带',
  rose: '玫瑰',
  scientist: '科学家',
  sidebar: '侧边栏',
  startup: '创业',
  swiss: '瑞士',
  teacher: '教师',
  timeline: '时间线',
  'two-column': '双栏',
  watercolor: '水彩',
  zigzag: '锯齿',
};

export const templateMap: Record<string, React.ComponentType<{ resume: Resume }>> = {
  academic: AcademicTemplate,
  architect: ArchitectTemplate,
  artistic: ArtisticTemplate,
  ats: AtsTemplate,
  berlin: BerlinTemplate,
  blocks: BlocksTemplate,
  bold: BoldTemplate,
  card: CardTemplate,
  classic: ClassicTemplate,
  clean: CleanTemplate,
  coder: CoderTemplate,
  compact: CompactTemplate,
  consultant: ConsultantTemplate,
  corporate: CorporateTemplate,
  creative: CreativeTemplate,
  designer: DesignerTemplate,
  developer: DeveloperTemplate,
  elegant: ElegantTemplate,
  engineer: EngineerTemplate,
  euro: EuroTemplate,
  executive: ExecutiveTemplate,
  finance: FinanceTemplate,
  formal: FormalTemplate,
  gradient: GradientTemplate,
  infographic: InfographicTemplate,
  japanese: JapaneseTemplate,
  legal: LegalTemplate,
  luxe: LuxeTemplate,
  magazine: MagazineTemplate,
  material: MaterialTemplate,
  medical: MedicalTemplate,
  metro: MetroTemplate,
  minimal: MinimalTemplate,
  modern: ModernTemplate,
  mosaic: MosaicTemplate,
  neon: NeonTemplate,
  nordic: NordicTemplate,
  professional: ProfessionalTemplate,
  retro: RetroTemplate,
  ribbon: RibbonTemplate,
  rose: RoseTemplate,
  scientist: ScientistTemplate,
  sidebar: SidebarTemplate,
  startup: StartupTemplate,
  swiss: SwissTemplate,
  teacher: TeacherTemplate,
  timeline: TimelineTemplate,
  'two-column': TwoColumnTemplate,
  watercolor: WatercolorTemplate,
  zigzag: ZigzagTemplate,
};
