import { useRef } from 'react';
import { Camera, X } from 'lucide-react';
import type { SectionComponentProps } from './helpers';
import { F, FieldWrapper, S } from './helpers';

export function PersonalInfo({ section, onUpdate }: SectionComponentProps) {
  const d = section.content as Record<string, unknown>;
  const u = (field: string, value: string) => onUpdate({ [field]: value });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const genderOptions = ['男', '女'];
  const politicalStatusOptions = ['群众', '共青团员', '中共预备党员', '中共党员', '民主党派'];
  const maritalStatusOptions = ['未婚', '已婚', '离异'];
  const educationLevelOptions = ['初中', '高中', '中专', '大专', '本科', '硕士', '博士', '博士后'];
  const ethnicityOptions = ['汉族', '蒙古族', '回族', '藏族', '维吾尔族', '苗族', '彝族', '壮族', '布依族', '朝鲜族', '满族', '侗族', '瑶族', '白族', '土家族', '哈尼族', '哈萨克族', '傣族', '黎族', '傈僳族', '佤族', '畲族', '高山族', '拉祜族', '水族', '东乡族', '纳西族', '景颇族', '柯尔克孜族', '土族', '达斡尔族', '仫佬族', '羌族', '布朗族', '撒拉族', '毛南族', '仡佬族', '锡伯族', '阿昌族', '普米族', '塔吉克族', '怒族', '乌孜别克族', '俄罗斯族', '鄂温克族', '德昂族', '保安族', '裕固族', '京族', '塔塔尔族', '独龙族', '鄂伦春族', '赫哲族', '门巴族', '珞巴族', '基诺族'];

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // TODO: 后端图片上传接口就绪后替换此逻辑
    const reader = new FileReader();
    reader.onload = (ev) => {
      u('avatar', ev.target?.result as string);
    };
    reader.readAsDataURL(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="relative flex h-24 w-20 shrink-0 items-center justify-center overflow-hidden rounded border-2 border-dashed border-border bg-muted transition-colors hover:border-muted-foreground hover:bg-muted/80"
        >
          {(d.avatar as string) ? (
            <img src={d.avatar as string} alt="Avatar" className="h-full w-full object-cover" />
          ) : (
            <Camera className="h-6 w-6 text-muted-foreground" />
          )}
        </button>
        <div className="flex flex-col gap-2">
          {(d.avatar as string) && (
            <button
              type="button"
              onClick={() => u('avatar', '')}
              className="inline-flex w-fit cursor-pointer items-center gap-1 rounded-md px-2 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <X className="h-3 w-3" />
              清除
            </button>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleAvatarChange}
          className="hidden"
        />
      </div>

      <FieldWrapper>
        <F label="姓名" value={(d.fullName as string) || ''} onChange={(e) => u('fullName', e.target.value)} />
        <F label="职位" value={(d.jobTitle as string) || ''} onChange={(e) => u('jobTitle', e.target.value)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="年龄" value={(d.age as string) || ''} onChange={(e) => u('age', e.target.value)} />
        <S label="性别" value={(d.gender as string) || ''} options={genderOptions} onChange={(v) => u('gender', v)} />
      </FieldWrapper>
      <FieldWrapper>
        <S label="政治面貌" value={(d.politicalStatus as string) || ''} options={politicalStatusOptions} onChange={(v) => u('politicalStatus', v)} />
        <S label="民族" value={(d.ethnicity as string) || ''} options={ethnicityOptions} onChange={(v) => u('ethnicity', v)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="工作年限" value={(d.yearsOfExperience as string) || ''} onChange={(e) => u('yearsOfExperience', e.target.value)} />
        <S label="最高学历" value={(d.educationLevel as string) || ''} options={educationLevelOptions} onChange={(v) => u('educationLevel', v)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="籍贯" value={(d.hometown as string) || ''} onChange={(e) => u('hometown', e.target.value)} />
        <F label="所在地" value={(d.location as string) || ''} onChange={(e) => u('location', e.target.value)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="邮箱" value={(d.email as string) || ''} onChange={(e) => u('email', e.target.value)} />
        <F label="电话" value={(d.phone as string) || ''} onChange={(e) => u('phone', e.target.value)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="微信" value={(d.wechat as string) || ''} onChange={(e) => u('wechat', e.target.value)} />
        <S label="婚姻状况" value={(d.maritalStatus as string) || ''} options={maritalStatusOptions} onChange={(v) => u('maritalStatus', v)} />
      </FieldWrapper>
      <FieldWrapper>
        <F label="期望薪资" value={(d.salary as string) || ''} onChange={(e) => u('salary', e.target.value)} />
        <F label="个人网站" value={(d.website as string) || ''} onChange={(e) => u('website', e.target.value)} />
      </FieldWrapper>
    </div>
  );
}

