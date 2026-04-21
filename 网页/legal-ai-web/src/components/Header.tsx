import { motion } from 'framer-motion';
import { Scale, Bot, User } from 'lucide-react';

export default function Header() {
  return (
    <motion.header
      className="relative z-10 h-[80px] flex items-center border-b border-purple-500/20"
      style={{
        background: 'rgba(15, 7, 41, 0.8)',
        backdropFilter: 'blur(12px)',
      }}
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div 
            className="flex items-center gap-3"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            <div className="relative">
              <div className="w-11 h-11 rounded-xl gradient-bg flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-lg bg-cyan-400/20 backdrop-blur-sm flex items-center justify-center border border-cyan-400/30">
                <Bot className="w-3 h-3 text-cyan-400" />
              </div>
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500 to-cyan-400 opacity-30 blur-xl -z-10" />
            </div>
          </motion.div>

          {/* Title */}
          <div className="flex-1 text-center">
            <motion.h1
              className="text-xl sm:text-2xl md:text-3xl font-bold gradient-text tracking-tight"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
            >
              智能司法辅助系统
            </motion.h1>
            <motion.p
              className="hidden sm:block text-xs md:text-sm text-slate-400 mt-0.5"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              基于深度学习的法律罪名预测平台
            </motion.p>
          </div>

          {/* User Avatar */}
          <motion.div
            className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500/20 to-cyan-400/20 border border-purple-500/30 flex items-center justify-center"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            <User className="w-5 h-5 text-purple-400" />
          </motion.div>
        </div>
      </div>
    </motion.header>
  );
}
