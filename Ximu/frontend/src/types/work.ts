export interface WorkTask {
  id: string;
  taskType: string;
  status: string;
  workspaceId?: string;
  metaInfo: {
    fileName?: string;
    src?: string;
    template?: string;
    title?: string;
  } | null;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}
