"""独立配音模块路径；配置与声音样本可通过环境显式指定。"""
import os
from pathlib import Path
VOICE_ROOT = Path(__file__).resolve().parent
PIPELINE_ROOT = Path(os.environ.get('LEMON_VOICE_CONFIG_ROOT', str(VOICE_ROOT.parent))).expanduser().resolve()
def find_pipeline_root(): return PIPELINE_ROOT
def find_voice_root(): return VOICE_ROOT
def clone_input_dir(): return Path(os.environ.get('LEMON_CLONE_INPUT_DIR', str(VOICE_ROOT / 'clone_input'))).expanduser().resolve()
