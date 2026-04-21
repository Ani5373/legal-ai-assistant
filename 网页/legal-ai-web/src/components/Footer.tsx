import { motion } from 'framer-motion';
import { Cpu, Layers, Sparkles } from 'lucide-react';

export default function Footer() {
  return (
    <motion.footer
      className="relative z-10 py-6 px-4"
      style={{
        background: 'rgba(10, 10, 10, 0.8)',
        backdropFilter: 'blur(12px)',
        borderTop: '1px solid rgba(168, 85, 247, 0.15)',
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.5 }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-wrap items-center justify-center gap-3 md:gap-6 text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>基于 RoBERTa 深度学习模型</span>
          </div>
          <span className="hidden md:inline text-slate-600">|</span>
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>长文本分层池化技术</span>
          </div>
          <span className="hidden md:inline text-slate-600">|</span>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span>Powered by Advanced Legal AI</span>
          </div>
        </div>
      </div>
    </motion.footer>
  );
}
