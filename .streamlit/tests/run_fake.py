"""Executa o app com o Supabase falso:  streamlit run tests/run_fake.py"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tests import fake_supabase  # noqa: E402

fake_supabase.install()
caminho = RAIZ / "portal.py"
exec(compile(caminho.read_text(), str(caminho), "exec"), {"__file__": str(caminho), "__name__": "__main__"})
