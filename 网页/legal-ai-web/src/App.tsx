import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import BackgroundEffects from './components/BackgroundEffects';
import Header from './components/Header';
import CaseInputCard from './components/CaseInputCard';
import Footer from './components/Footer';
import SummaryCard from './components/analysis/SummaryCard';
import PredictionPanel from './components/analysis/PredictionPanel';
import StepTimeline from './components/analysis/StepTimeline';
import CaseGraphPanel from './components/graph/CaseGraphPanel';
import LawReferencePanel from './components/analysis/LawReferencePanel';
import ReportPanel from './components/analysis/ReportPanel';
import WarningPanel from './components/analysis/WarningPanel';
import type { CaseAnalysisResponse } from './types/analysis';
import { analyzeCaseStream } from './utils/api';
import { saveToHistory, getHistoryById } from './utils/storage';

export default function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<CaseAnalysisResponse | null>(null);
  const [lastSubmittedText, setLastSubmittedText] = useState('');
  const [currentStage, setCurrentStage] = useState<string>('');

  const runAnalysis = async (text: string) => {
    setIsLoading(true);
    setError(null);
    setAnalysis(null);
    setCurrentStage('开始分析...');

    try {
      await analyzeCaseStream(text, undefined, (chunk) => {
        if (chunk.type === 'start') {
          setCurrentStage('开始分析案件');
        } else if (chunk.type === 'stage') {
          setCurrentStage(chunk.message || '处理中...');
        } else if (chunk.type === 'fact_extraction_complete') {
          // 事实抽取完成，更新部分结果
          setCurrentStage('事实抽取完成');
          if (chunk.data) {
            setAnalysis((prev) => ({
              ...(prev || {} as CaseAnalysisResponse),
              nodes: chunk.data.nodes || [],
              edges: chunk.data.edges || [],
              steps: chunk.data.steps || [],
            }));
          }
        } else if (chunk.type === 'charge_prediction_complete') {
          setCurrentStage('罪名预测完成');
          if (chunk.data) {
            setAnalysis((prev) => ({
              ...(prev || {} as CaseAnalysisResponse),
              predictions: chunk.data.predictions || [],
              steps: chunk.data.steps || [],
            }));
          }
        } else if (chunk.type === 'law_retrieval_complete') {
          setCurrentStage('法条检索完成');
          if (chunk.data) {
            setAnalysis((prev) => ({
              ...(prev || {} as CaseAnalysisResponse),
              nodes: chunk.data.nodes || [],
              edges: chunk.data.edges || [],
              steps: chunk.data.steps || [],
            }));
          }
        } else if (chunk.type === 'complete') {
          // 全部完成
          setCurrentStage('');
          if (chunk.data) {
            setAnalysis(chunk.data as CaseAnalysisResponse);
            saveToHistory(chunk.data as CaseAnalysisResponse);
          }
          setIsLoading(false);
        } else if (chunk.type === 'error') {
          setError(chunk.message || '分析失败');
          setIsLoading(false);
          setCurrentStage('');
        }
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '分析失败，请稍后重试';
      setError(errorMessage);
      setIsLoading(false);
      setCurrentStage('');
    }
  };

  const handleSubmit = (text: string) => {
    setLastSubmittedText(text);
    void runAnalysis(text);
  };

  const handleClear = () => {
    setAnalysis(null);
    setError(null);
    setLastSubmittedText('');
    setCurrentStage('');
  };

  const handleRetry = () => {
    if (!lastSubmittedText.trim()) {
      setError(null);
      return;
    }
    void runAnalysis(lastSubmittedText);
  };

  const handleLoadHistory = (historyId: number) => {
    console.log('App.tsx - 加载历史记录，ID:', historyId);
    const historyRecord = getHistoryById(historyId);
    console.log('App.tsx - 获取到的历史记录:', historyRecord);
    
    if (!historyRecord) {
      console.error('App.tsx - 未找到历史记录');
      setError('未找到该历史记录');
      return;
    }
    
    if (!historyRecord.fullAnalysis) {
      console.error('App.tsx - 历史记录缺少完整分析数据');
      setError('该历史记录不包含完整分析数据，请重新分析案件');
      return;
    }
    
    console.log('App.tsx - 设置分析结果');
    setAnalysis(historyRecord.fullAnalysis);
    setError(null);
    setCurrentStage('');
    setLastSubmittedText(historyRecord.fullAnalysis.text);
  };

  return (
    <div className="min-h-screen flex flex-col relative bg-slate-950">
      <BackgroundEffects />

      <Header />

      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 xl:px-12 py-8 lg:py-12">
        <div className="max-w-7xl mx-auto w-full space-y-8">
          {/* 案情输入区 */}
          <CaseInputCard
            onSubmit={handleSubmit}
            isLoading={isLoading}
            onClear={handleClear}
            onHistoryUpdate={() => {}}
            onLoadHistory={handleLoadHistory}
          />

          {/* Loading 状态 */}
          <AnimatePresence>
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex flex-col items-center justify-center py-16"
              >
                <Loader2 className="w-12 h-12 text-purple-400 animate-spin mb-4" />
                <p className="text-lg text-slate-300">{currentStage || '正在分析案件...'}</p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error 状态 */}
          <AnimatePresence>
            {error && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="rounded-2xl bg-red-500/10 backdrop-blur-xl border border-red-500/30 p-6"
              >
                <div className="flex items-start gap-4">
                  <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-red-400 mb-2">分析失败</h3>
                    <p className="text-slate-300 mb-4">{error}</p>
                    <button
                      onClick={handleRetry}
                      className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                      重试
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* 分析结果区 */}
          <AnimatePresence>
            {analysis && !error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-8"
              >
                {/* 核心摘要 */}
                {analysis.case_id && <SummaryCard analysis={analysis} />}

                {/* 罪名预测 + 步骤时间线 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {analysis.predictions && analysis.predictions.length > 0 && (
                    <PredictionPanel predictions={analysis.predictions} />
                  )}
                  {analysis.steps && analysis.steps.length > 0 && (
                    <StepTimeline steps={analysis.steps} />
                  )}
                </div>

                {/* 知识图谱 */}
                {analysis.nodes && analysis.nodes.length > 0 && (
                  <CaseGraphPanel nodes={analysis.nodes} edges={analysis.edges || []} />
                )}

                {/* 法条量刑 + 报告 */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {analysis.nodes && analysis.nodes.length > 0 && (
                    <LawReferencePanel 
                      nodes={analysis.nodes} 
                      predictions={analysis.predictions}
                    />
                  )}
                  {analysis.report && (
                    <ReportPanel report={analysis.report} />
                  )}
                </div>

                {/* 系统警告 */}
                {analysis.warnings && analysis.warnings.length > 0 && (
                  <WarningPanel warnings={analysis.warnings} metadata={analysis.metadata} />
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* 空状态提示 */}
          <AnimatePresence>
            {!isLoading && !error && !analysis && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-center py-16"
              >
                <p className="text-lg text-slate-400">
                  请输入案情描述开始分析
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      <Footer />
    </div>
  );
}
