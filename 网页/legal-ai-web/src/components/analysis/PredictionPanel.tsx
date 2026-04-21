import { motion } from 'framer-motion';
import { Trophy } from 'lucide-react';
import type { ChargePrediction } from '../../types/analysis';
import { formatProbability } from '../../utils/format';
import { useMemo } from 'react';

interface PredictionPanelProps {
  predictions: ChargePrediction[];
}

export default function PredictionPanel({ predictions }: PredictionPanelProps) {
  const sortedPredictions = useMemo(() => {
    return [...predictions].sort((a, b) => {
      if (a.rank !== undefined && b.rank !== undefined) {
        return a.rank - b.rank;
      }
      return b.probability - a.probability;
    });
  }, [predictions]);

  if (predictions.length === 0) {
    return (
      <div className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6">
        <h3 className="text-xl font-bold text-white mb-4">罪名预测</h3>
        <div className="text-center text-slate-400 py-8">
          暂无预测结果
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6"
    >
      <h3 className="text-xl font-bold text-white mb-6">罪名预测</h3>

      <div className="space-y-3">
        {sortedPredictions.map((pred, index) => (
          <motion.div
            key={pred.label}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className={`relative rounded-xl p-4 border transition-all ${
              index === 0
                ? 'bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border-purple-500/50'
                : 'bg-slate-800/30 border-slate-700/30'
            }`}
          >
            {/* 排名标识 */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                {index === 0 && (
                  <Trophy className="w-5 h-5 text-amber-400" />
                )}
                <span className={`font-bold ${index === 0 ? 'text-xl text-white' : 'text-lg text-slate-200'}`}>
                  {pred.label}
                </span>
              </div>
              <span className="text-sm text-slate-400">
                {pred.source}
              </span>
            </div>

            {/* 概率进度条 */}
            <div className="relative">
              <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pred.probability * 100}%` }}
                  transition={{ duration: 0.8, delay: index * 0.1 }}
                  className={`h-full rounded-full ${
                    index === 0
                      ? 'bg-gradient-to-r from-purple-500 to-cyan-500'
                      : 'bg-slate-500'
                  }`}
                />
              </div>
              <div className={`text-right mt-1 text-sm font-medium ${
                index === 0 ? 'text-purple-400' : 'text-slate-400'
              }`}>
                {formatProbability(pred.probability)}
              </div>
            </div>

            {/* Rank 信息 */}
            {pred.rank !== undefined && (
              <div className="text-xs text-slate-500 mt-1">
                排名: {pred.rank}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
