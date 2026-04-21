"""
对比模型效果
"""

import glob
import json
import os
from pathlib import Path

import torch
from train import HierarchicalRoBERTa, LegalTextDataset, collate_fn, evaluate
from transformers import BertTokenizer
from torch.utils.data import DataLoader

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TRAINING_DIR = PROJECT_ROOT / '模型训练'
PROCESSED_DATA_DIR = TRAINING_DIR / '处理后数据'
PRETRAINED_MODEL_DIR = TRAINING_DIR / '预训练模型'
TRAINING_OUTPUT_DIR = TRAINING_DIR / '训练输出'

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model_path = str(PRETRAINED_MODEL_DIR / 'chinese-roberta-wwm-ext')
output_dir = str(TRAINING_OUTPUT_DIR)

tokenizer = BertTokenizer.from_pretrained(model_path)

val_dataset = LegalTextDataset(
    str(PROCESSED_DATA_DIR / 'val_processed.json'), tokenizer,
    max_chunk_length=510, max_chunks=2, max_samples=10000
)
val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False, collate_fn=collate_fn)

with open(PROCESSED_DATA_DIR / 'label_mapping.json', 'r', encoding='utf-8') as f:
    num_classes = json.load(f)['num_classes']

results = []

# 找最后一个检查点
checkpoints = sorted(glob.glob(os.path.join(output_dir, 'checkpoint_epoch_*.pt')))
if checkpoints:
    ckpt_path = checkpoints[-1]
    ckpt = torch.load(ckpt_path, weights_only=False)
    model = HierarchicalRoBERTa(model_path, num_classes).to(device)
    model.load_state_dict(ckpt['model_state_dict'])
    acc, f1, loss = evaluate(model, val_loader, device)
    results.append(f'最后模型 Epoch {ckpt["epoch"]}: Acc={acc:.4f}, F1={f1:.4f}, Loss={loss:.4f}')
    del model; torch.cuda.empty_cache()

# 找最佳模型
best_path = os.path.join(output_dir, 'best_model.pt')
if os.path.exists(best_path):
    ckpt = torch.load(best_path, weights_only=False)
    model = HierarchicalRoBERTa(model_path, num_classes).to(device)
    model.load_state_dict(ckpt['model_state_dict'])
    acc, f1, loss = evaluate(model, val_loader, device)
    results.append(f'最佳模型 Epoch {ckpt["epoch"]}: Acc={acc:.4f}, F1={f1:.4f}, Loss={loss:.4f}')
    del model; torch.cuda.empty_cache()

# 保存结果
output = '\n'.join(results)
print(output)
with open(os.path.join(output_dir, 'eval_results.txt'), 'w') as f:
    f.write(output)
print(f'\n结果已保存到 {output_dir}/eval_results.txt')
