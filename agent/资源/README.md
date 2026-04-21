# 多 Agent 本地资源说明

本目录存放多 Agent 智能定罪系统第一阶段可直接使用的本地资源文件。

## 文件说明

### `entity_types.json`

- 用途：提供 `FactExtractorAgent` 的实体抽取 schema。
- 来源：不是数据集原生标注，而是结合当前业务目标人工定义的标准化类型清单。
- 主要字段：
  - `type`：实体类型名称
  - `description`：抽取目标说明
  - `required_graph_fields`：进入图谱前必须具备的字段
  - `optional_fields`：后续可补充字段

### `relation_types.json`

- 用途：提供 `FactExtractorAgent` 和 `Coordinator` 的关系抽取/图谱建边规范。
- 来源：同样为面向业务流程定义的关系类型，不是原始数据集中直接提供的标注。
- 主要字段：
  - `relation`：关系名称
  - `source_types` / `target_types`：允许的源节点/目标节点类型
  - `description`：关系含义

### `law_knowledge_base.json`

- 用途：提供 `LawRetrieverAgent` 第一版本地知识索引。
- 来源：由 `CAIL2018` 原始样本中 `accusation`、`relevant_articles`、`term_of_imprisonment`、`punish_of_money` 汇总得到。
- 当前可直接支持：
  - 罪名 -> 常见法条编号
  - 法条编号 -> 常见罪名
  - 罪名/法条 -> 刑期分布统计
  - 罪名/法条 -> 罚金分布统计
  - 代表性案例片段
- 当前尚不包含：
  - 法条全文
  - 司法解释正文
  - 人工编写的量刑裁判规则文本

### `test_cases.json`

- 用途：提供前后端联调、图谱展示和 Agent 回归测试样本。
- 选择策略：
  - 覆盖当前 10 类 BERT 标签
  - 增补多罪名、长文本、多法条、高刑期、高罚金样本
- 主要字段：
  - `fact`：输入案情
  - `expected`：期望罪名/法条/刑期/罚金
  - `selection_reason`：为什么选这条样本

## 构建命令

在项目根目录执行：

```powershell
python agent/脚本/build_agent_resources.py
```

默认使用以下数据源：

- `模型训练/原始数据/final_all_data/exercise_contest/data_train.json`
- `模型训练/原始数据/final_all_data/exercise_contest/data_valid.json`

如需替换输入文件，可手动指定：

```powershell
python agent/脚本/build_agent_resources.py `
  --input 模型训练/原始数据/final_all_data/exercise_contest/data_train.json `
  --input 模型训练/原始数据/final_all_data/exercise_contest/data_valid.json `
  --output-dir agent/资源
```

## 后续接入建议

### `FactExtractorAgent`

- 将 `entity_types.json` 和 `relation_types.json` 作为 prompt 中的固定 schema。
- 要求模型输出 `nodes + edges`，并严格限制 `type`、`relation` 只能取本目录清单中的值。

### `LawRetrieverAgent`

- 先按预测罪名命中 `accusation_catalog`。
- 再补充对应 `article_catalog` 和量刑统计摘要。
- 如果后续补齐法条全文，可继续在同一份 JSON 中扩展 `text`、`interpretation`、`sentencing_rules` 字段。

### 回归测试

- 优先用 `test_cases.json` 做接口回归。
- 如果 `FactExtractorAgent` 需要更严格评估，建议后续为其中 10 到 20 条样本人工补一版 `golden graph`。
