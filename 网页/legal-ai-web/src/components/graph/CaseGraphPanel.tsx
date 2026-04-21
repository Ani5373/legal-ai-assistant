import { motion } from 'framer-motion';
import { useState, useRef, useMemo, useEffect } from 'react';
import { Network, X, Info } from 'lucide-react';
import cytoscape from 'cytoscape';
import type { GraphNode, GraphEdge } from '../../types/analysis';

interface CaseGraphPanelProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// 获取节点颜色（优化后的配色方案）
function getNodeColor(type: string): string {
  const colorMap: Record<string, string> = {
    '案件': '#FFD700',      // 金色 - 案件根节点
    '人物': '#90EE90',      // 浅绿色 - 犯罪嫌疑人
    '受害人': '#DDA0DD',    // 紫色 - 受害人
    '行为': '#FFA500',      // 橙色 - 行为动作
    '金额': '#00CED1',      // 青色 - 金额
    '时间': '#87CEEB',      // 天蓝色 - 时间
    '地点': '#98FB98',      // 淡绿色 - 地点
    '伤情': '#FF6B6B',      // 红色 - 伤情
    '证据': '#BA55D3',      // 中紫色 - 证据
    '罪名': '#FF6347',      // 番茄红 - 罪名
    '法条': '#4169E1',      // 皇家蓝 - 法条
    '量刑规则': '#9370DB',  // 中紫色 - 量刑
    '组织机构': '#20B2AA',  // 浅海绿 - 组织
    '情节': '#FFB6C1',      // 浅粉色 - 情节
    '物品': '#F0E68C',      // 卡其色 - 物品
  };
  return colorMap[type] || '#94a3b8';
}

// 获取节点图标（已禁用）
function getNodeIcon(type: string): string {
  // 不再使用emoji图标
  return '';
}

// 获取边的样式（根据关系类型）
function getEdgeStyle(relation: string): { color: string; width: number; style: string } {
  // 核心关系 - 粗实线
  if (['实施', '作用于', '侵害'].includes(relation)) {
    return { color: '#FF8C00', width: 3, style: 'solid' };
  }
  // 法律关系 - 粗实线
  if (['指向罪名', '构成', '对应法条', '依据'].includes(relation)) {
    return { color: '#DC143C', width: 4, style: 'solid' };
  }
  // 量刑关系 - 中等实线
  if (['约束量刑', '量刑', '影响量刑'].includes(relation)) {
    return { color: '#4B0082', width: 2, style: 'solid' };
  }
  // 归属关系 - 虚线
  if (['从属于案件', '从属于', '归属'].includes(relation)) {
    return { color: '#999999', width: 1, style: 'dashed' };
  }
  // 其他关系 - 普通实线
  return { color: '#64748b', width: 2, style: 'solid' };
}

export default function CaseGraphPanel({ nodes, edges }: CaseGraphPanelProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const elements = useMemo(() => {
    const nodeElements = nodes.map(node => {
      return {
        data: {
          id: node.id,
          label: node.label,  // 直接使用原始标签，不添加图标
          type: node.type,
          color: getNodeColor(node.type),
          description: node.description,
          source: node.source,
          metadata: node.metadata,
          rawLabel: node.label,
        },
      };
    });

    const edgeElements = edges.map(edge => {
      const edgeStyle = getEdgeStyle(edge.relation);
      
      return {
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.relation,
          evidence: edge.evidence,
          metadata: edge.metadata,
          edgeColor: edgeStyle.color,
          edgeWidth: edgeStyle.width,
          edgeStyle: edgeStyle.style,
        },
      };
    });

    return [...nodeElements, ...edgeElements];
  }, [nodes, edges]);

  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return;

    // 销毁旧实例
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // 创建新实例
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            'label': 'data(label)',
            'color': '#ffffff',  // 白色文字
            'font-size': 14,
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '80px',
            'height': '80px',
            'border-width': 3,
            'border-color': '#1e293b',
            'text-wrap': 'wrap',
            'text-max-width': '100px',
            // 移除文字背景
            'text-outline-color': '#1e293b',
            'text-outline-width': 2,
          },
        },
        {
          selector: 'node[type = "案件"]',
          style: {
            'width': '100px',
            'height': '100px',
            'border-width': 4,
            'font-size': 16,
          },
        },
        {
          selector: 'node[type = "罪名"]',
          style: {
            'width': '90px',
            'height': '90px',
            'border-width': 3,
            'font-size': 15,
          },
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(edgeWidth)',
            'line-color': 'data(edgeColor)',
            'target-arrow-color': 'data(edgeColor)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'color': '#ffffff',  // 白色文字
            'font-size': 12,
            'font-weight': 'bold',
            'text-rotation': 'autorotate',
            'text-margin-y': -12,
            // 移除文字背景，添加描边
            'text-outline-color': '#1e293b',
            'text-outline-width': 2,
            'line-style': 'data(edgeStyle)',
          },
        },
        {
          selector: 'edge[edgeStyle = "dashed"]',
          style: {
            'line-style': 'dashed',
            'line-dash-pattern': [6, 3],
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 5,
            'border-color': '#8b5cf6',
            'box-shadow': '0 0 20px #8b5cf6',
          },
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#8b5cf6',
            'target-arrow-color': '#8b5cf6',
            'width': 'calc(data(edgeWidth) + 2)',
          },
        },
      ],
      layout: {
        name: 'breadthfirst',
        fit: true,
        padding: 50,
        directed: true,
        spacingFactor: 2.0,
        avoidOverlap: true,
        nodeDimensionsIncludeLabels: true,
        // 故事流式布局：从左到右
        roots: nodes.filter(n => n.type === '案件').map(n => `#${n.id}`).join(','),
      },
      minZoom: 0.3,
      maxZoom: 2,
    });

    // 事件监听
    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      const node = nodes.find(n => n.id === nodeData.id);
      setSelectedNode(node || null);
      setSelectedEdge(null);
    });

    cy.on('tap', 'edge', (evt) => {
      const edgeData = evt.target.data();
      const edge = edges.find(e => e.id === edgeData.id);
      setSelectedEdge(edge || null);
      setSelectedNode(null);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
        setSelectedEdge(null);
      }
    });

    cyRef.current = cy;

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [elements, nodes, edges]);

  if (nodes.length === 0) {
    return (
      <div className="rounded-2xl bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Network className="w-5 h-5 text-cyan-400" />
          <h3 className="text-xl font-bold text-white">知识图谱</h3>
        </div>
        <div className="text-center text-slate-400 py-8">
          暂无图谱数据
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
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-cyan-400" />
          <h3 className="text-xl font-bold text-white">知识图谱</h3>
        </div>
        <div className="text-sm text-slate-400">
          {nodes.length} 节点 / {edges.length} 边
        </div>
      </div>

      {/* 操作提示 */}
      <div className="mb-3 flex items-center gap-4 text-xs text-slate-400">
        <span>💡 提示：</span>
        <span>点击节点查看详情</span>
        <span>•</span>
        <span>滚轮缩放</span>
        <span>•</span>
        <span>拖拽移动</span>
      </div>

      {/* 图谱容器 */}
      <div className="relative">
        <div
          ref={containerRef}
          className="w-full h-[500px] lg:h-[600px] rounded-xl bg-gradient-to-br from-slate-900/80 to-slate-800/80 border border-slate-700/30 shadow-2xl"
        />

        {/* 节点详情弹窗 */}
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute top-4 right-4 w-80 bg-slate-800/95 backdrop-blur-xl rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-gradient-to-r from-slate-800 to-slate-700">
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-lg shadow-lg border-2 border-slate-900"
                  style={{ backgroundColor: getNodeColor(selectedNode.type) }}
                />
                <div>
                  <div className="text-xs text-slate-400">节点类型</div>
                  <div className="font-bold text-white">{selectedNode.type}</div>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-300" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="p-3 rounded-lg bg-slate-700/30">
                <div className="text-xs text-slate-400 mb-1.5">节点标签</div>
                <div className="text-base font-bold text-white">{selectedNode.label}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-700/30">
                <div className="text-xs text-slate-400 mb-1.5">节点描述</div>
                <div className="text-sm text-slate-200 leading-relaxed">{selectedNode.description}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-700/30">
                <div className="text-xs text-slate-400 mb-1.5">数据来源</div>
                <div className="text-sm text-cyan-400 font-mono">{selectedNode.source}</div>
              </div>
              {Object.keys(selectedNode.metadata).length > 0 && (
                <div className="p-3 rounded-lg bg-slate-700/30">
                  <div className="text-xs text-slate-400 mb-1.5">元数据</div>
                  <div className="text-xs font-mono text-slate-300 bg-slate-900/50 p-3 rounded-lg max-h-40 overflow-y-auto">
                    {JSON.stringify(selectedNode.metadata, null, 2)}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* 边详情弹窗 */}
        {selectedEdge && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute top-4 right-4 w-80 bg-slate-800/95 backdrop-blur-xl rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between p-4 border-b border-slate-700/50 bg-gradient-to-r from-slate-800 to-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                  <Info className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-400">关系详情</div>
                  <div className="font-bold text-white">{selectedEdge.relation}</div>
                </div>
              </div>
              <button
                onClick={() => setSelectedEdge(null)}
                className="p-2 hover:bg-slate-600/50 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-300" />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="p-3 rounded-lg bg-slate-700/30">
                <div className="text-xs text-slate-400 mb-1.5">关系类型</div>
                <div className="text-base font-bold text-white">{selectedEdge.relation}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-700/30">
                <div className="text-xs text-slate-400 mb-1.5">证据说明</div>
                <div className="text-sm text-slate-200 leading-relaxed">{selectedEdge.evidence}</div>
              </div>
              {Object.keys(selectedEdge.metadata).length > 0 && (
                <div className="p-3 rounded-lg bg-slate-700/30">
                  <div className="text-xs text-slate-400 mb-1.5">元数据</div>
                  <div className="text-xs font-mono text-slate-300 bg-slate-900/50 p-3 rounded-lg max-h-40 overflow-y-auto">
                    {JSON.stringify(selectedEdge.metadata, null, 2)}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* 图例 */}
      <div className="mt-4 p-4 rounded-xl bg-slate-900/30 border border-slate-700/30">
        <div className="text-sm font-semibold text-slate-300 mb-3">图例说明</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {Array.from(new Set(nodes.map(n => n.type))).map(type => (
            <div key={type} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/50 hover:bg-slate-800/80 transition-colors">
              <div
                className="w-4 h-4 rounded-full border-2 border-slate-700"
                style={{ backgroundColor: getNodeColor(type) }}
              />
              <span className="text-xs font-medium text-slate-300">{type}</span>
            </div>
          ))}
        </div>
        
        {/* 关系类型说明 */}
        <div className="mt-4 pt-4 border-t border-slate-700/30">
          <div className="text-xs text-slate-400 mb-2">关系类型：</div>
          <div className="flex flex-wrap gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 bg-orange-500"></div>
              <span className="text-slate-400">核心关系</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 bg-red-600"></div>
              <span className="text-slate-400">法律关系</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 bg-purple-700"></div>
              <span className="text-slate-400">量刑关系</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 bg-gray-500 border-dashed border-t-2 border-gray-500"></div>
              <span className="text-slate-400">归属关系</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
