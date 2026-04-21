import { motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { ExecutionStep } from '../../types/analysis';
import { formatDuration, calculateDuration, getStatusColor, getStatusBgColor } from '../../utils/format';

interface StepTimelineProps {
  steps: ExecutionStep[];
}

export default function StepTimeline({ steps }: StepTimelineProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const displaySteps = isExpanded ? steps : steps.slice(0, 2);
  const hasMore = steps.length > 2;

  if (steps.length === 0) {
    return (
      <div className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6">
        <h3 className="text-xl font-bold text-white mb-4">推理步骤</h3>
        <div className="text-center text-slate-400 py-8">
          暂无执行步骤
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-white">推理步骤</h3>
        {hasMore && (
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
                <span>显示全部 ({steps.length})</span>
              </>
            )}
          </button>
        )}
      </div>

      <div className="relative">
        {/* 时间线轴 */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-purple-500 via-cyan-500 to-slate-700" />

        {/* 步骤列表 */}
        <div className="space-y-4">
          {displaySteps.map((step, index) => {
            const duration = calculateDuration(step.started_at, step.ended_at);
            const hasError = Boolean(step.details?.error);

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="relative pl-14"
              >
                {/* 状态图标 */}
                <div className={`absolute left-4 top-1 w-5 h-5 rounded-full border-2 border-slate-800 flex items-center justify-center ${String(getStatusBgColor(step.status))}`}>
                  {step.status === 'completed' && <CheckCircle className="w-3 h-3 text-emerald-400" />}
                  {step.status === 'failed' && <XCircle className="w-3 h-3 text-red-400" />}
                  {step.status === 'skipped' && <AlertCircle className="w-3 h-3 text-amber-400" />}
                </div>

                {/* 步骤内容 */}
                <div className={`rounded-xl p-4 border ${
                  hasError
                    ? 'bg-red-500/10 border-red-500/30'
                    : 'bg-slate-800/30 border-slate-700/30'
                }`}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-bold text-white">{step.name}</h4>
                      <p className="text-sm text-slate-400">{step.agent}</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Clock className="w-4 h-4" />
                      <span>{formatDuration(duration)}</span>
                    </div>
                  </div>

                  <p className="text-sm text-slate-300 mb-2">{step.summary}</p>

                  {/* 状态标签 */}
                  <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium`}>
                    <span className={`${getStatusBgColor(step.status)} ${getStatusColor(step.status)}`}>
                      {step.status === 'completed' && '已完成'}
                      {step.status === 'failed' && '失败'}
                      {step.status === 'skipped' && '跳过'}
                    </span>
                  </div>

                  {/* 错误信息 */}
                  {hasError && (
                    <div className="mt-2 p-2 bg-red-500/20 rounded border border-red-500/30">
                      <p className="text-sm text-red-400 font-mono">{JSON.stringify(step.details.error)}</p>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
