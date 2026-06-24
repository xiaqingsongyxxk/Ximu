import { useNavigate } from 'react-router-dom'
import { FileQuestion } from 'lucide-react'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex h-screen items-center justify-center bg-muted">
      <div className="flex flex-col items-center justify-center text-gray-400 gap-4">
        <FileQuestion className="w-16 h-16 text-gray-400/40" strokeWidth={1.5} />
        <div className="text-center">
          <p className="text-lg text-gray-300 mb-1">页面不存在</p>
          <p className="text-sm text-gray-500">您访问的页面可能已被删除或不存在</p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/workspace')}
          className="mt-2 px-4 py-2 rounded-lg bg-pink-500/20 text-pink-400 hover:bg-pink-500/30 transition-colors text-sm"
        >
          返回工作空间列表
        </button>
      </div>
    </div>
  )
}
