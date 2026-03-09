"""一次性入库脚本：处理私有文档并创建向量索引。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 兼容直接执行 scripts/ingest.py：将项目根目录加入模块搜索路径。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ingest_service import ingest_documents


def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="简历资料一次性入库脚本")
    parser.add_argument(
        "--input_dir",
        required=True,
        help="私有文档目录（支持 pdf/docx/txt/md）",
    )
    args = parser.parse_args()

    result = ingest_documents(args.input_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
