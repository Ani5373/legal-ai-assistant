import { useState, useEffect, type ChangeEvent, type FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Zap, Loader2, RotateCcw, Trash2, Clock, ChevronDown, ChevronUp, Eye } from 'lucide-react';
import { getHistory, deleteHistoryById, type AnalysisHistory } from '../utils/storage';

interface CaseInputCardProps {
  onSubmit: (text: string) => void;
  isLoading: boolean;
  onClear: () => void;
  onHistoryUpdate: () => void;
  onLoadHistory: (historyId: number) => void;
}

export default function CaseInputCard({ onSubmit, isLoading, onClear, onHistoryUpdate, onLoadHistory }: CaseInputCardProps) {
  const [text, setText] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<AnalysisHistory[]>(() => getHistory());
  const MAX_CHARS = 2000;

  const loadHistoryList = () => {
    setHistory(getHistory());
  };

  useEffect(() => {
    if (!isLoading) {
      const refreshTimer = window.setTimeout(() => {
        loadHistoryList();
      }, 0);
      return () => window.clearTimeout(refreshTimer);
    }
  }, [isLoading]);

  useEffect(() => {
    onHistoryUpdate();
  }, [history.length, onHistoryUpdate]);

  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    if (e.target.value.length <= MAX_CHARS) {
      setText(e.target.value);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim() && !isLoading) {
      onSubmit(text);
    }
  };

  const handleClear = () => {
    setText('');
    onClear();
  };

  const handleDeleteHistory = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteHistoryById(id);
    loadHistoryList();
  };

  const handleClearAllHistory = () => {
    setHistory([]);
    localStorage.removeItem('caseHistory');
  };

  const handleViewHistory = (id: number) => {
    console.log('点击历史记录，ID:', id);
    const historyRecord = getHistory().find(h => h.id === id);
    console.log('找到的历史记录:', historyRecord);
    onLoadHistory(id);
    setShowHistory(false);
  };

  const charCount = text.length;
  const isOverLimit = charCount > MAX_CHARS;
  const isNearLimit = charCount > MAX_CHARS * 0.9;

  return (
    <motion.div
      className="h-full flex flex-col"
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      <div className="glass-card p-6 md:p-8 flex flex-col h-full">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <FileText className="w-5 h-5 text-purple-400" />
            </div>
            <h2 className="text-xl font-semibold text-white">案情描述输入</h2>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadHistoryList();
                setShowHistory(!showHistory);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-700/50 text-slate-300 hover:bg-slate-600/50 transition-colors text-sm"
            >
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">历史</span>
              {history.length > 0 && (
                <span className="bg-purple-500 text-white text-xs px-1.5 py-0.5 rounded-full">{history.length}</span>
              )}
              {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {text && (
              <button
                onClick={handleClear}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors text-sm"
              >
                <RotateCcw className="w-4 h-4" />
                <span className="hidden sm:inline">重置</span>
              </button>
            )}
          </div>
        </div>

        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 overflow-hidden"
            >
              <div className="bg-slate-900/30 rounded-xl border border-slate-700/30 max-h-[400px] overflow-y-auto">
                <div className="p-3 flex items-center justify-between border-b border-slate-700/30 sticky top-0 bg-slate-900/50">
                  <span className="text-sm text-slate-400">历史记录 ({history.length})</span>
                  {history.length > 0 && (
                    <button
                      onClick={handleClearAllHistory}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors"
                    >
                      清除全部
                    </button>
                  )}
                </div>
                {history.length === 0 ? (
                  <div className="p-8 text-center text-slate-500">
                    <Clock className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>暂无历史记录</p>
                    <p className="text-xs mt-1">分析完成后会自动保存到这里</p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-700/30">
                    {history.slice().reverse().map((record) => (
                      <div 
                        key={record.id} 
                        className="p-3 group hover:bg-slate-800/30 transition-colors cursor-pointer relative"
                        onClick={() => {
                          console.log('整个卡片被点击');
                          handleViewHistory(record.id);
                        }}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-300 line-clamp-2 mb-1">{record.text}</p>
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                              <span>{new Date(record.timestamp).toLocaleString('zh-CN')}</span>
                              {record.predictions[0] && (
                                <>
                                  <span className="text-purple-400">{record.predictions[0].label}</span>
                                  <span className="text-cyan-400">{(record.predictions[0].probability * 100).toFixed(1)}%</span>
                                </>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1 flex-shrink-0 relative z-10">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                console.log('查看按钮被点击');
                                handleViewHistory(record.id);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-purple-500/20 text-slate-500 hover:text-purple-400 transition-all"
                              title="查看完整报告"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => {
                                console.log('删除按钮被点击');
                                handleDeleteHistory(record.id, e);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-all"
                              title="删除"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1">
          <div className="relative flex-1 min-h-[200px]">
            <textarea
              value={text}
              onChange={handleTextChange}
              placeholder="请输入详细的案情描述内容，系统将自动分析并预测相关罪名..."
              disabled={isLoading}
              className="w-full h-full min-h-[180px] p-4 rounded-xl bg-slate-900/50 border-2 text-white placeholder-slate-500 resize-none outline-none transition-all duration-300 scrollbar-thin textarea-glow"
              style={{
                borderColor: isNearLimit 
                  ? 'rgba(249, 115, 22, 0.5)' 
                  : 'rgba(148, 163, 184, 0.2)',
              }}
            />
            
            <div className="absolute bottom-3 right-3">
              <span 
                className={`text-xs font-medium px-2 py-1 rounded-full transition-colors ${
                  isOverLimit 
                    ? 'bg-red-500/20 text-red-400' 
                    : isNearLimit 
                      ? 'bg-orange-500/20 text-orange-400' 
                      : 'bg-slate-700/50 text-slate-400'
                }`}
              >
                {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
              </span>
            </div>
          </div>

          <motion.button
            type="submit"
            disabled={!text.trim() || isLoading || isOverLimit}
            className="w-full py-4 px-6 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
            style={{
              background: text.trim() && !isLoading && !isOverLimit
                ? 'linear-gradient(135deg, #A855F7 0%, #9333EA 50%, #7C3AED 100%)'
                : 'linear-gradient(135deg, #6B21A8 0%, #581C87 100%)',
              boxShadow: text.trim() && !isLoading && !isOverLimit
                ? '0 10px 40px -10px rgba(168, 85, 247, 0.5)'
                : 'none',
            }}
            whileHover={text.trim() && !isLoading && !isOverLimit ? { scale: 1.02 } : {}}
            whileTap={text.trim() && !isLoading && !isOverLimit ? { scale: 0.98 } : {}}
          >
            {isLoading ? (
              <>
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}>
                  <Loader2 className="w-5 h-5" />
                </motion.div>
                <span>分析中...</span>
              </>
            ) : (
              <>
                <Zap className="w-5 h-5" />
                <span>开始智能分析</span>
              </>
            )}
          </motion.button>
        </form>
      </div>
    </motion.div>
  );
}
