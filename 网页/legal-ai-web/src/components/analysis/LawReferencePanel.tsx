import { motion } from 'framer-motion';
import { Scale, Gavel, FileText, Loader2 } from 'lucide-react';
import type { GraphNode, ChargePrediction, SimilarCase } from '../../types/analysis';
import { useMemo, useState, useEffect } from 'react';
import { fetchSimilarCases } from '../../utils/similarCaseApi';

interface LawReferencePanelProps {
  nodes: GraphNode[];
  predictions?: ChargePrediction[];
}

export default function LawReferencePanel({ nodes, predictions }: LawReferencePanelProps) {
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);

  const lawNodes = useMemo(() => {
    return nodes.filter(node => node.type === '法条');
  }, [nodes]);

  const sentencingNodes = useMemo(() => {
    return nodes.filter(node => node.type === '量刑规则');
  }, [nodes]);

  // 获取类案推荐
  useEffect(() => {
    if (!predictions || predictions.length === 0) {
      return;
    }

    const loadSimilarCases = async () => {
      setLoadingSimilar(true);
      try {
        const charges = predictions.slice(0, 3).map(p => p.label);
        const cases = await fetchSimilarCases(charges, 3);
        setSimilarCases(cases);
      } catch (error) {
        console.error('加载类案推荐失败:', error);
      } finally {
        setLoadingSimilar(false);
      }
    };

    void loadSimilarCases();
  }, [predictions]);

  if (lawNodes.length === 0 && sentencingNodes.length === 0) {
    return (
      <div className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6">
        <h3 className="text-xl font-bold text-white mb-4">法条与量刑参考</h3>
        <div className="text-center text-slate-400 py-8">
          暂无法条与量刑参考
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6"
    >
      <h3 className="text-xl font-bold text-white mb-6">法条与量刑参考</h3>

      <div className="space-y-6">
        {/* 法条列表 */}
        {lawNodes.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Scale className="w-5 h-5 text-cyan-400" />
              <h4 className="text-lg font-semibold text-slate-200">相关法条</h4>
            </div>
            <div className="space-y-2">
              {lawNodes.map((node, index) => {
                const articleNumber = node.metadata?.article_number;
                const sampleCount = node.metadata?.sample_count;

                return (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                    className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30"
                  >
                    <div className="font-bold text-white mb-1">{node.label}</div>
                    <p className="text-sm text-slate-300 mb-2">{node.description}</p>
                    <div className="flex gap-4 text-xs text-slate-400">
                      {articleNumber !== undefined && (
                        <span>条文号: {String(articleNumber)}</span>
                      )}
                      {sampleCount !== undefined && (
                        <span>样本数: {String(sampleCount)}</span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}

        {/* 量刑规则列表 */}
        {sentencingNodes.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Gavel className="w-5 h-5 text-amber-400" />
              <h4 className="text-lg font-semibold text-slate-200">量刑参考</h4>
            </div>
            <div className="space-y-2">
              {sentencingNodes.map((node, index) => {
                const imprisonment = node.metadata?.imprisonment_summary as {
                  average_months?: number;
                  min_months?: number;
                  max_months?: number;
                } | undefined;
                const fine = node.metadata?.fine_summary as {
                  average_amount?: number;
                  min_amount?: number;
                  max_amount?: number;
                } | undefined;

                return (
                  <motion.div
                    key={node.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: (lawNodes.length + index) * 0.05 }}
                    className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30"
                  >
                    <div className="font-bold text-white mb-1">{node.label}</div>
                    <p className="text-sm text-slate-300 mb-2">{node.description}</p>

                    {/* 刑期信息 */}
                    {imprisonment && (
                      <div className="text-xs text-slate-400 mb-1">
                        <span className="font-medium">刑期:</span>{' '}
                        平均 {imprisonment.average_months?.toFixed(1)} 月
                        ({imprisonment.min_months} - {imprisonment.max_months} 月)
                      </div>
                    )}

                    {/* 罚金信息 */}
                    {fine && (
                      <div className="text-xs text-slate-400">
                        <span className="font-medium">罚金:</span>{' '}
                        平均 {fine.average_amount?.toFixed(2)} 元
                        ({fine.min_amount} - {fine.max_amount} 元)
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}

        {/* 类案推荐 */}
        {predictions && predictions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-5 h-5 text-purple-400" />
              <h4 className="text-lg font-semibold text-slate-200">类案推荐</h4>
            </div>
            
            {loadingSimilar ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                <span className="ml-2 text-sm text-slate-400">加载类案中...</span>
              </div>
            ) : similarCases.length > 0 ? (
              <div className="space-y-2">
                {similarCases.map((similarCase, index) => (
                  <motion.div
                    key={similarCase.case_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: (lawNodes.length + sentencingNodes.length + index) * 0.05 }}
                    className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30 hover:border-purple-500/30 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="font-bold text-white text-sm">案件 {index + 1}</div>
                      <div className="text-xs text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded">
                        相似度: {(similarCase.similarity_score * 100).toFixed(0)}%
                      </div>
                    </div>
                    <p className="text-sm text-slate-300 mb-2 line-clamp-2">{similarCase.text}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {similarCase.charges.map((charge, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-0.5 rounded bg-slate-700/50 text-slate-300"
                        >
                          {charge}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center text-slate-400 py-4 text-sm">
                暂无类案推荐
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
