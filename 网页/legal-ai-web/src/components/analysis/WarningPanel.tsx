import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, Info, AlertCircle } from 'lucide-react';

interface WarningPanelProps {
  warnings: string[];
  metadata: Record<string, unknown>;
}

export default function WarningPanel({ warnings, metadata }: WarningPanelProps) {
  const fromCache = metadata?.from_cache === true;
  const securityCheck = metadata?.security_check as {
    passed?: boolean;
    risk_level?: string;
    stage?: string;
  } | undefined;

  const hasWarnings = warnings.length > 0 || fromCache || (securityCheck && !securityCheck.passed);

  if (!hasWarnings) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
        className="rounded-2xl bg-emerald-500/10 backdrop-blur-xl border border-emerald-500/30 p-4"
      >
        <div className="flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-emerald-400" />
          <span className="text-emerald-400 font-medium">系统状态正常</span>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6"
    >
      <h3 className="text-xl font-bold text-white mb-4">系统提示</h3>

      <div className="space-y-3">
        {/* 缓存提示 */}
        {fromCache && (
          <div className="flex items-start gap-3 bg-blue-500/10 rounded-lg p-3 border border-blue-500/30">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-blue-400 mb-1">缓存命中</div>
              <div className="text-sm text-slate-300">当前结果来自内存缓存</div>
            </div>
          </div>
        )}

        {/* 安全检查警告 */}
        {securityCheck && !securityCheck.passed && (
          <div className="flex items-start gap-3 bg-red-500/10 rounded-lg p-3 border border-red-500/30">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-medium text-red-400 mb-1">安全检查未通过</div>
              <div className="text-sm text-slate-300">
                风险等级: <span className="font-bold text-red-400">{securityCheck.risk_level}</span>
                {securityCheck.stage && <span className="ml-2">阶段: {securityCheck.stage}</span>}
              </div>
            </div>
          </div>
        )}

        {/* 其他警告 */}
        {warnings.map((warning, index) => (
          <div
            key={index}
            className="flex items-start gap-3 bg-amber-500/10 rounded-lg p-3 border border-amber-500/30"
          >
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-slate-300">{warning}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
