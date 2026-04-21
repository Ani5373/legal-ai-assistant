"""
配置管理
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 项目路径
    SERVICE_DIR: Path = Path(__file__).resolve().parent.parent
    PROJECT_ROOT: Path = SERVICE_DIR.parent

    # 模型配置
    MODEL_WEIGHTS_PATH: Path | None = None
    LABEL_MAPPING_PATH: Path | None = None
    LABEL2ID_PATH: Path | None = None
    TOKENIZER_MODEL_PATH: Path | None = None

    # 资源配置
    LAW_KNOWLEDGE_BASE_PATH: Path | None = None

    # 服务配置
    HOST: str = "127.0.0.1"
    PORT: int = 8111
    RELOAD: bool = True

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]
    CORS_CREDENTIALS: bool = False
    CORS_METHODS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    # 内存和安全配置
    ENABLE_MEMORY_CACHE: bool = True
    ENABLE_SECURITY_CHECK: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_model_weights_path(self) -> Path:
        """获取模型权重路径"""
        if self.MODEL_WEIGHTS_PATH:
            return Path(self.MODEL_WEIGHTS_PATH)
        return self.PROJECT_ROOT / "模型训练" / "训练输出" / "best_model.pt"

    def get_label_mapping_path(self) -> Path:
        """获取标签映射路径"""
        if self.LABEL_MAPPING_PATH:
            return Path(self.LABEL_MAPPING_PATH)
        return self.PROJECT_ROOT / "模型训练" / "处理后数据" / "label_mapping.json"

    def get_label2id_path(self) -> Path:
        """获取 label2id 路径"""
        if self.LABEL2ID_PATH:
            return Path(self.LABEL2ID_PATH)
        return self.PROJECT_ROOT / "模型训练" / "处理后数据" / "label2id.json"

    def get_tokenizer_model_path(self) -> Path:
        """获取 tokenizer 模型路径"""
        if self.TOKENIZER_MODEL_PATH:
            return Path(self.TOKENIZER_MODEL_PATH)
        return self.PROJECT_ROOT / "模型训练" / "预训练模型" / "chinese-roberta-wwm-ext"

    def get_law_knowledge_base_path(self) -> Path:
        """获取法条知识库路径"""
        if self.LAW_KNOWLEDGE_BASE_PATH:
            return Path(self.LAW_KNOWLEDGE_BASE_PATH)
        return self.PROJECT_ROOT / "agent" / "资源" / "law_knowledge_base.json"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
