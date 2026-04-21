"""
基于 RoBERTa 的法律长文本罪名预测系统 - 训练脚本

核心特色：
1. 长文本分块策略：滑动窗口切分长文本，解决512 Token限制
2. 分层池化策略：对多个Chunk的[CLS]向量进行Mean-Pooling融合
3. 自动保存最佳模型：基于Macro-F1指标
"""

import json
import os
import random
from pathlib import Path
import numpy as np
from tqdm import tqdm
from sklearn.metrics import accuracy_score, f1_score

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.amp.autocast_mode import autocast
from torch.amp.grad_scaler import GradScaler
from transformers import BertTokenizer, BertModel, get_linear_schedule_with_warmup


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TRAINING_DIR = PROJECT_ROOT / "模型训练"
RAW_DATA_DIR = TRAINING_DIR / "原始数据"
PROCESSED_DATA_DIR = TRAINING_DIR / "处理后数据"
PRETRAINED_MODEL_DIR = TRAINING_DIR / "预训练模型"
TRAINING_OUTPUT_DIR = TRAINING_DIR / "训练输出"


# ====================== 设置随机种子保证可复现性 ======================
def set_seed(seed=42):
    """设置随机种子，确保实验可复现"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ====================== 数据集类定义 ======================
class LegalTextDataset(Dataset):
    """
    法律文本数据集类

    功能：
    1. 加载JSON Lines格式的数据
    2. 预先tokenize并缓存，避免每个epoch重复计算
    3. 对长文本进行分块处理
    """

    def __init__(self, data_path, tokenizer, max_chunk_length=510, max_chunks=10, max_samples=None):
        data_path = str(data_path)
        self.tokenizer = tokenizer
        self.max_chunk_length = max_chunk_length
        self.max_chunks = max_chunks
        self.max_len = max_chunk_length + 2

        suffix = f'_cached_mcl{max_chunk_length}_mc{max_chunks}'
        if max_samples:
            suffix += f'_n{max_samples}'
        cache_path = data_path.replace('.json', suffix + '.pt')
        print(f'加载缓存: {cache_path}')
        self.cached_data = torch.load(cache_path, weights_only=True)
        print(f'缓存加载完成，样本数: {len(self.cached_data)}')

    def _process_text(self, text, label):
        """预先处理文本：tokenize + 分块 + 编码"""
        tokens = self.tokenizer.tokenize(text)

        chunked_input_ids = []
        chunked_attention_masks = []

        for i in range(0, len(tokens), self.max_chunk_length):
            chunk = tokens[i:i + self.max_chunk_length]
            chunk = ['[CLS]'] + chunk + ['[SEP]']

            input_ids = self.tokenizer.convert_tokens_to_ids(chunk)
            attention_mask = [1] * len(input_ids)

            # Padding到固定长度
            if len(input_ids) < self.max_len:
                pad_len = self.max_len - len(input_ids)
                input_ids += [0] * pad_len
                attention_mask += [0] * pad_len

            chunked_input_ids.append(input_ids)
            chunked_attention_masks.append(attention_mask)

            if len(chunked_input_ids) >= self.max_chunks:
                break

        return {
            'input_ids': torch.tensor(chunked_input_ids, dtype=torch.long),
            'attention_mask': torch.tensor(chunked_attention_masks, dtype=torch.long),
            'label': torch.tensor(label, dtype=torch.float)  # 多标签需要float
        }

    @staticmethod
    def preprocess_and_cache(data_path, tokenizer, max_chunk_length=510, max_chunks=10, max_samples=None):
        """在主进程中调用，预处理并保存缓存"""
        data_path = str(data_path)
        suffix = f'_cached_mcl{max_chunk_length}_mc{max_chunks}'
        if max_samples:
            suffix += f'_n{max_samples}'
        cache_path = data_path.replace('.json', suffix + '.pt')
        if os.path.exists(cache_path):
            print(f'缓存已存在: {cache_path}')
            return

        max_len = max_chunk_length + 2
        cached_data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(tqdm(f, desc=f'预处理 {data_path}')):
                if max_samples and i >= max_samples:
                    break
                data = json.loads(line.strip())
                tokens = tokenizer.tokenize(data['fact'])
                chunked_input_ids = []
                chunked_attention_masks = []
                for i in range(0, len(tokens), max_chunk_length):
                    chunk = tokens[i:i + max_chunk_length]
                    chunk = ['[CLS]'] + chunk + ['[SEP]']
                    input_ids = tokenizer.convert_tokens_to_ids(chunk)
                    attention_mask = [1] * len(input_ids)
                    if len(input_ids) < max_len:
                        pad_len = max_len - len(input_ids)
                        input_ids += [0] * pad_len
                        attention_mask += [0] * pad_len
                    chunked_input_ids.append(input_ids)
                    chunked_attention_masks.append(attention_mask)
                    if len(chunked_input_ids) >= max_chunks:
                        break
                cached_data.append({
                    'input_ids': torch.tensor(chunked_input_ids, dtype=torch.long),
                    'attention_mask': torch.tensor(chunked_attention_masks, dtype=torch.long),
                    'label': torch.tensor(data['label'], dtype=torch.float)  # 多标签需要float
                })
        torch.save(cached_data, cache_path)
        print(f'缓存已保存: {cache_path}')

    def __len__(self):
        """返回数据集大小"""
        return len(self.cached_data)

    def __getitem__(self, idx):
        """直接返回预处理好的数据"""
        return self.cached_data[idx]


# ====================== 自定义Collate函数 ======================
def collate_fn(batch):
    """
    将一个batch的样本合并

    处理逻辑：
    1. 不同样本的chunk数量可能不同
    2. 需要对chunks进行padding，使batch中所有样本的chunk数量一致
    """
    # 找到batch中最大的chunk数量
    max_chunks = max([item['input_ids'].size(0) for item in batch])

    batch_input_ids = []
    batch_attention_masks = []
    batch_labels = []

    for item in batch:
        input_ids = item['input_ids']  # [num_chunks, seq_len]
        attention_mask = item['attention_mask']  # [num_chunks, seq_len]
        label = item['label']

        num_chunks = input_ids.size(0)
        seq_len = input_ids.size(1)

        # 如果当前样本的chunk数量小于max_chunks，进行padding
        if num_chunks < max_chunks:
            padding = torch.zeros(max_chunks - num_chunks, seq_len, dtype=torch.long)
            input_ids = torch.cat([input_ids, padding], dim=0)
            attention_mask = torch.cat([attention_mask, padding], dim=0)

        batch_input_ids.append(input_ids)
        batch_attention_masks.append(attention_mask)
        batch_labels.append(label)

    # Stack成batch tensor
    # Shape: [batch_size, max_chunks, seq_len]
    batch_input_ids = torch.stack(batch_input_ids, dim=0)
    batch_attention_masks = torch.stack(batch_attention_masks, dim=0)
    batch_labels = torch.stack(batch_labels, dim=0)

    return {
        'input_ids': batch_input_ids,
        'attention_mask': batch_attention_masks,
        'labels': batch_labels
    }


# ====================== 模型定义：层次化RoBERTa ======================
class HierarchicalRoBERTa(nn.Module):
    """
    层次化RoBERTa模型

    架构说明：
    1. 底层：BertModel 用于提取每个Chunk的语义表示
    2. 中层：Mean-Pooling 对多个Chunk的[CLS]向量进行融合
    3. 顶层：Linear 分类层输出罪名预测

    输入：长文本经分块后的多个Chunk
    输出：10个罪名的logits
    """

    def __init__(self, model_path, num_classes=10, dropout=0.1):
        """
        初始化模型

        参数：
        - model_path: 预训练模型路径
        - num_classes: 分类类别数（10个罪名）
        - dropout: Dropout概率
        """
        super(HierarchicalRoBERTa, self).__init__()

        # ========== 底层：BERT模型 ==========
        self.bert = BertModel.from_pretrained(model_path)
        self.hidden_size = self.bert.config.hidden_size  # 通常为768

        # ========== 中层：Dropout（防止过拟合）==========
        self.dropout = nn.Dropout(dropout)

        # ========== 顶层：分类器 ==========
        self.classifier = nn.Linear(self.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        """
        前向传播

        参数：
        - input_ids: [batch_size, num_chunks, seq_len] 分块后的输入
        - attention_mask: [batch_size, num_chunks, seq_len] 注意力掩码

        返回：
        - logits: [batch_size, num_classes] 预测logits
        - cls_embeddings: [batch_size, num_chunks, hidden_size] 所有Chunk的[CLS]向量
        """
        batch_size = input_ids.size(0)
        num_chunks = input_ids.size(1)
        seq_len = input_ids.size(2)

        # ========== Reshape：将batch和chunk维度合并 ==========
        # [batch_size, num_chunks, seq_len] -> [batch_size * num_chunks, seq_len]
        # 这样可以一次性送入BERT处理所有chunks
        input_ids_flat = input_ids.view(-1, seq_len)
        attention_mask_flat = attention_mask.view(-1, seq_len)

        # ========== BERT前向传播 ==========
        # 获取所有层的输出，包括pooler_output
        outputs = self.bert(
            input_ids=input_ids_flat,
            attention_mask=attention_mask_flat
        )

        # 提取[CLS]向量（每个序列的第一个token的表示）
        # Shape: [batch_size * num_chunks, hidden_size]
        cls_embeddings_flat = outputs.last_hidden_state[:, 0, :]

        # ========== Reshape：恢复chunk维度 ==========
        # [batch_size * num_chunks, hidden_size] -> [batch_size, num_chunks, hidden_size]
        cls_embeddings = cls_embeddings_flat.view(batch_size, num_chunks, -1)

        # 创建一个mask来标记真实的chunk（padding的chunk不计入）
        # 通过attention_mask的第一个token来判断是否是padding chunk
        chunk_mask = attention_mask[:, :, 0].unsqueeze(-1).float()  # [batch, num_chunks, 1]

        # ========== Mean-Pooling：融合多个Chunk的[CLS]向量（向量化）==========
        # 零化padding chunk的嵌入，然后求和除以有效chunk数
        masked_embeddings = cls_embeddings * chunk_mask  # [batch, num_chunks, hidden]
        sum_embeddings = masked_embeddings.sum(dim=1)  # [batch, hidden]
        valid_counts = chunk_mask.sum(dim=1).clamp(min=1)  # 避免除零
        pooled_output = sum_embeddings / valid_counts  # [batch, hidden]

        # ========== Dropout ==========
        pooled_output = self.dropout(pooled_output)

        # ========== 分类层 ==========
        # [batch_size, hidden_size] -> [batch_size, num_classes]
        logits = self.classifier(pooled_output)

        return logits, cls_embeddings


# ====================== 评估函数 ======================
def evaluate(model, dataloader, device):
    """
    在验证集上评估模型性能（多标签版本）

    返回：
    - accuracy: 子集准确率（所有标签都正确才算正确）
    - macro_f1: 宏平均F1分数
    - avg_loss: 平均损失
    """
    model.eval()

    all_preds = []
    all_labels = []
    total_loss = 0
    loss_fn = nn.BCEWithLogitsLoss()

    with torch.no_grad():
        for batch in tqdm(dataloader, desc='评估中'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            logits, _ = model(input_ids, attention_mask)

            # 多标签损失
            loss = loss_fn(logits, labels)
            total_loss += loss.item()

            # 阈值过滤：概率 > 0.5 的为正类
            probs = torch.sigmoid(logits)
            preds = (probs > 0.5).float()

            all_preds.append(preds.cpu().numpy())
            all_labels.append(labels.cpu().numpy())

    import numpy as np
    all_preds = np.vstack(all_preds)
    all_labels = np.vstack(all_labels)

    # 计算子集准确率
    subset_accuracy = (all_preds == all_labels).all(axis=1).mean()

    # 计算宏平均F1
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)

    avg_loss = total_loss / len(dataloader)

    return subset_accuracy, macro_f1, avg_loss


# ====================== 训练主函数 ======================
def train():
    """主训练函数"""

    # ========== 配置参数 ==========
    # RTX 4060 Laptop (8GB) + 14核CPU + 16GB RAM 优化配置
    config = {
        'model_path': str(PRETRAINED_MODEL_DIR / 'chinese-roberta-wwm-ext'),
        'train_data': str(PROCESSED_DATA_DIR / 'train_processed.json'),
        'val_data': str(PROCESSED_DATA_DIR / 'val_processed.json'),
        'label_mapping': str(PROCESSED_DATA_DIR / 'label_mapping.json'),
        'output_dir': str(TRAINING_OUTPUT_DIR),
        'max_chunk_length': 510,
        'max_chunks': 2,
        'batch_size': 4,  # 减少以适应显存
        'use_amp': True,  # 启用混合精度加速
        'num_epochs': 10,
        'learning_rate': 2e-5,
        'warmup_ratio': 0.1,
        'weight_decay': 0.01,
        'dropout': 0.1,
        'gradient_clip': 1.0,
        'gradient_accumulation_steps': 4,  # 梯度累积，等效batch_size=16
        'num_train_samples': 100000,  # 用10万条训练
        'num_val_samples': 10000,  # 用1万条验证
        'seed': 42
    }

    # 创建输出目录
    os.makedirs(config['output_dir'], exist_ok=True)

    # 设置随机种子
    set_seed(config['seed'])

    # 加载标签映射
    with open(config['label_mapping'], 'r', encoding='utf-8') as f:
        label_mapping = json.load(f)
    num_classes = label_mapping['num_classes']
    print(f'类别数: {num_classes}')
    print(f'罪名: {label_mapping["id2label"]}')

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # ========== 加载Tokenizer ==========
    print('\n========== 加载Tokenizer ==========')
    tokenizer = BertTokenizer.from_pretrained(config['model_path'])
    print(f'Tokenizer加载完成，词汇表大小: {len(tokenizer)}')

    # ========== 加载数据集 ==========
    print('\n========== 加载数据集 ==========')

    # 先在主进程预处理并缓存（避免多进程重复处理）
    LegalTextDataset.preprocess_and_cache(
        config['train_data'], tokenizer,
        config['max_chunk_length'], config['max_chunks'],
        max_samples=config['num_train_samples']
    )
    LegalTextDataset.preprocess_and_cache(
        config['val_data'], tokenizer,
        config['max_chunk_length'], config['max_chunks'],
        max_samples=config['num_val_samples']
    )

    # 加载训练集
    train_dataset = LegalTextDataset(
        config['train_data'], tokenizer,
        max_chunk_length=config['max_chunk_length'],
        max_chunks=config['max_chunks'],
        max_samples=config['num_train_samples']
    )
    print(f'训练集大小: {len(train_dataset)}')

    # 加载验证集
    val_dataset = LegalTextDataset(
        config['val_data'], tokenizer,
        max_chunk_length=config['max_chunk_length'],
        max_chunks=config['max_chunks'],
        max_samples=config['num_val_samples']
    )
    print(f'验证集大小: {len(val_dataset)}')

    # ========== 创建数据加载器 ==========
    print('\n========== 创建数据加载器 ==========')
    train_dataloader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=True
    )

    val_dataloader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=True
    )
    print(f'训练batch数量: {len(train_dataloader)}')
    print(f'验证batch数量: {len(val_dataloader)}')

    # ========== 初始化模型 ==========
    print('\n========== 初始化模型 ==========')
    model = HierarchicalRoBERTa(
        model_path=config['model_path'],
        num_classes=num_classes,
        dropout=config['dropout']
    ).to(device)

    # torch.compile加速（PyTorch 2.0+）
    # if hasattr(torch, 'compile'):
    #     model = torch.compile(model)
    #     print('已启用 torch.compile 加速')

    # 统计参数数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f'总参数量: {total_params:,}')
    print(f'可训练参数量: {trainable_params:,}')

    # ========== 设置优化器和学习率调度器 ==========
    print('\n========== 设置优化器 ==========')
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config['learning_rate'],
        weight_decay=config['weight_decay']
    )

    # 计算warmup步数
    num_training_steps = len(train_dataloader) * config['num_epochs']
    num_warmup_steps = int(num_training_steps * config['warmup_ratio'])

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=num_warmup_steps,
        num_training_steps=num_training_steps
    )

    print(f'总训练步数: {num_training_steps}')
    print(f'Warmup步数: {num_warmup_steps}')

    # 计算类别权重（平衡数据分布）
    print('\n========== 计算类别权重 ==========')
    all_labels = torch.stack([item['label'] for item in train_dataset])
    pos_counts = all_labels.sum(dim=0)  # 每个类别的正样本数
    pos_weight = (len(train_dataset) / (num_classes * pos_counts + 1e-6)).to(device)
    print(f'各类别正样本数: {pos_counts.tolist()}')
    print(f'类别权重: {pos_weight.tolist()}')

    # 损失函数（多标签用BCEWithLogitsLoss + pos_weight）
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    # ========== 训练循环 ==========
    print('\n' + '=' * 60)
    print('开始训练')
    print('=' * 60 + '\n')

    best_macro_f1 = 0.0
    global_step = 0
    start_epoch = 0

    scaler = GradScaler() if config.get('use_amp', False) else None

    # ========== 断点续训：查找最新的检查点 ==========
    saved_models_dir = config['output_dir']
    existing_checkpoints = []
    for f in os.listdir(saved_models_dir):
        if f.startswith('checkpoint_epoch_') and f.endswith('.pt'):
            epoch_num = int(f.replace('checkpoint_epoch_', '').replace('.pt', ''))
            existing_checkpoints.append((epoch_num, f))

    if existing_checkpoints:
        existing_checkpoints.sort(reverse=True)
        latest_epoch, latest_file = existing_checkpoints[0]
        checkpoint_path = os.path.join(saved_models_dir, latest_file)
        print(f'加载检查点: {checkpoint_path}')
        checkpoint = torch.load(checkpoint_path, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        best_macro_f1 = checkpoint['best_macro_f1']
        global_step = checkpoint['global_step']
        start_epoch = checkpoint['epoch']
        print(f'从 Epoch {start_epoch + 1} 继续训练，当前最佳 Macro-F1: {best_macro_f1:.4f}')

    for epoch in range(start_epoch, config['num_epochs']):
        print(f'\n========== Epoch {epoch + 1}/{config["num_epochs"]} ==========')

        model.train()
        epoch_loss = 0
        optimizer.zero_grad(set_to_none=True)

        # 训练
        progress_bar = tqdm(train_dataloader, desc=f'训练 Epoch {epoch + 1}')
        for step, batch in enumerate(progress_bar):
            # 将数据移到GPU
            input_ids = batch['input_ids'].to(device, non_blocking=True)
            attention_mask = batch['attention_mask'].to(device, non_blocking=True)
            labels = batch['labels'].to(device, non_blocking=True)

            # 前向传播
            if scaler:
                with autocast(device_type='cuda'):
                    logits, _ = model(input_ids, attention_mask)
                    loss = loss_fn(logits, labels)
                    loss = loss / config['gradient_accumulation_steps']
                scaler.scale(loss).backward()
            else:
                logits, _ = model(input_ids, attention_mask)
                loss = loss_fn(logits, labels)
                loss = loss / config['gradient_accumulation_steps']
                loss.backward()

            # 梯度累积：达到累积步数后更新参数
            if (step + 1) % config['gradient_accumulation_steps'] == 0:
                if scaler:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config['gradient_clip'])
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config['gradient_clip'])
                    optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1

            # 记录损失（还原累积前的loss值）
            epoch_loss += loss.item() * config['gradient_accumulation_steps']

            # 更新进度条
            progress_bar.set_postfix({'loss': f'{loss.item() * config["gradient_accumulation_steps"]:.4f}'})

        avg_train_loss = epoch_loss / len(train_dataloader)
        print(f'\n训练平均损失: {avg_train_loss:.4f}')

        # ========== 验证 ==========
        print('\n========== 验证 ==========')
        accuracy, macro_f1, avg_val_loss = evaluate(model, val_dataloader, device)
        print(f'验证集准确率: {accuracy:.4f}')
        print(f'验证集 Macro-F1: {macro_f1:.4f}')
        print(f'验证集平均损失: {avg_val_loss:.4f}')

        # ========== 保存检查点（每个epoch）==========
        checkpoint_path = os.path.join(config['output_dir'], f'checkpoint_epoch_{epoch + 1}.pt')
        torch.save({
            'epoch': epoch + 1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_macro_f1': best_macro_f1,
            'global_step': global_step,
            'config': config
        }, checkpoint_path)
        print(f'检查点已保存: checkpoint_epoch_{epoch + 1}.pt')

        # ========== 保存最佳模型 ==========
        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_model_path = os.path.join(config['output_dir'], 'best_model.pt')
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'best_macro_f1': best_macro_f1,
                'config': config
            }, best_model_path)
            print(f'\n🎉 保存最佳模型！Macro-F1: {best_macro_f1:.4f}')
            print(f'模型保存路径: {best_model_path}')
        else:
            print(f'\n当前Macro-F1: {macro_f1:.4f}，最佳Macro-F1: {best_macro_f1:.4f}')

    # ========== 训练结束 ==========
    print('\n' + '=' * 60)
    print('训练完成！')
    print('=' * 60)
    print(f'最佳 Macro-F1: {best_macro_f1:.4f}')


# ====================== 主程序入口 ======================
if __name__ == '__main__':
    train()
