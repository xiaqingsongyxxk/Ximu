export interface JdAnalysis {
  id: number;
  resumeId: string;
  overallScore: number;
  atsScore: number;
  summary: string;
  keywordMatches: string[];
  missingKeywords: string[];
  suggestions: any[];
  createdAt: string;
}

export interface SubResume {
  id: string;
  title: string;
  jobTitle?: string;
  jobDescription?: string;
  matchScore?: number;
  latestAnalysis?: JdAnalysis;
  createdAt: string;
  updatedAt: string;
}

export interface Workspace {
  id: string;
  workspaceId: string | null;
  title: string;
  template: string;
  themeConfig: Record<string, unknown>;
  isDefault: boolean;
  language: string;
  shareToken: string | null;
  isPublic: boolean;
  sharePassword: string | null;
  viewCount: number;
  subResumeIds: string[];
  createdAt: string;
  updatedAt: string;
}
