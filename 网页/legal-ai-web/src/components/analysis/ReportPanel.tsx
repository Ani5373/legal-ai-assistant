import { motion } from 'framer-motion';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReportPanelProps {
  report: string;
}

export default function ReportPanel({ report }: ReportPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!report) {
    return (
      <div className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-purple-400" />
          <h3 className="text-xl font-bold text-white">分析报告</h3>
        </div>
        <div className="text-center text-slate-400 py-8">
          暂无分析报告
        </div>
      </div>
    );
  }

  // 计算报告长度，判断是否需要折叠
  const reportLines = report.split('\n').length;
  const shouldCollapse = reportLines > 15;
  const displayReport = !shouldCollapse || isExpanded ? report : report.split('\n').slice(0, 15).join('\n') + '\n\n...';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-purple-400" />
          <h3 className="text-xl font-bold text-white">分析报告</h3>
        </div>
        {shouldCollapse && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors text-sm"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                <span>收起</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                <span>显示全部</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* 报告内容 */}
      <div className={`prose prose-invert prose-slate max-w-none relative ${!isExpanded && shouldCollapse ? 'max-h-[400px] overflow-hidden' : ''}`}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold text-white mb-4 mt-6 first:mt-0">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-semibold text-slate-100 mb-3 mt-5">{children}</h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-lg font-semibold text-slate-200 mb-2 mt-4">{children}</h3>
            ),
            p: ({ children }) => (
              <p className="text-slate-300 leading-relaxed mb-3">{children}</p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-inside text-slate-300 space-y-1 mb-3">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-inside text-slate-300 space-y-1 mb-3">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="text-slate-300">{children}</li>
            ),
            strong: ({ children }) => (
              <strong className="font-bold text-white">{children}</strong>
            ),
            code: ({ children }) => (
              <code className="bg-slate-700/50 px-1.5 py-0.5 rounded text-sm font-mono text-cyan-400">{children}</code>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-purple-500/50 pl-4 italic text-slate-400 my-3">{children}</blockquote>
            ),
          }}
        >
          {displayReport}
        </ReactMarkdown>
        
        {/* 渐变遮罩效果（折叠时） */}
        {!isExpanded && shouldCollapse && (
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-slate-800/50 via-slate-800/80 to-transparent pointer-events-none" />
        )}
      </div>
      
      {/* 展开提示（折叠时） */}
      {!isExpanded && shouldCollapse && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <button
            onClick={() => setIsExpanded(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-slate-700/30 hover:bg-slate-700/50 text-slate-300 hover:text-white transition-all group"
          >
            <span className="text-sm">内容较长，点击查看完整报告</span>
            <ChevronDown className="w-4 h-4 group-hover:translate-y-0.5 transition-transform" />
          </button>
        </div>
      )}
    </motion.div>
  );
}
