import { motion } from 'framer-motion';
import { FileText, Network, Shield, TrendingUp } from 'lucide-react';
import type { CaseAnalysisResponse } from '../../types/analysis';
import { formatProbability } from '../../utils/format';

interface SummaryCardProps {
  analysis: CaseAnalysisResponse;
}

export default function SummaryCard({ analysis }: SummaryCardProps) {
  const topPrediction = analysis.predictions[0];
  const graphStats = analysis.metadata?.graph_summary as { node_count?: number; edge_count?: number } | undefined;
  const securityCheck = analysis.metadata?.security_check as {
    passed?: boolean;
    risk_level?: string;
    stage?: string;
  } | undefined;

  const nodeCount = graphStats?.node_count ?? analysis.nodes.length;
  const edgeCount = graphStats?.edge_count ?? analysis.edges.length;
  const securityStatus = securityCheck?.passed === true
    ? '通过'
    : securityCheck?.passed === false
      ? '未通过'
      : '未提供';
  const securityStatusClass = securityCheck?.passed === true
    ? 'text-emerald-400'
    : securityCheck?.passed === false
      ? 'text-red-400'
      : 'text-slate-300';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-xl border border-slate-700/50 p-6 lg:p-8"
    >
      {/* 背景装饰 */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-500/10 to-cyan-500/10 rounded-full blur-3xl" />

      <div className="relative z-10">
        {/* 标题 */}
        <h2 className="text-2xl lg:text-3xl font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent mb-6">
          案件分析摘要
        </h2>

        {/* 核心信息网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          {/* 最高候选罪名 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <TrendingUp className="w-4 h-4" />
              <span>最高候选罪名</span>
            </div>
            <div className="text-xl lg:text-2xl font-bold text-white">
              {topPrediction?.label || '无'}
            </div>
            {topPrediction && (
              <div className="text-sm text-purple-400 mt-1">
                置信度 {formatProbability(topPrediction.probability)}
              </div>
            )}
          </div>

          {/* 案件编号 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <FileText className="w-4 h-4" />
              <span>案件编号</span>
            </div>
            <div className="text-lg font-mono text-white truncate">
              {analysis.case_id}
            </div>
          </div>

          {/* 图谱统计 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <Network className="w-4 h-4" />
              <span>知识图谱</span>
            </div>
            <div className="text-lg font-bold text-white">
              {nodeCount} 节点 / {edgeCount} 边
            </div>
          </div>

          {/* 安全状态 */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
            <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
              <Shield className="w-4 h-4" />
              <span>安全检查</span>
            </div>
            <div className={`text-lg font-bold ${securityStatusClass}`}>
              {securityStatus}
            </div>
            {securityCheck?.risk_level && (
              <div className="text-sm text-slate-400 mt-1">
                风险等级: {securityCheck.risk_level}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
