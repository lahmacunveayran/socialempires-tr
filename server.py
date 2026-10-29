"""Social Empires Türkçe sunucusunu başlatır: python server.py"""

import os
import sys

if os.name == "nt":
    os.system("title Social Empires Sunucusu")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from oyun.sunucu import calistir  # noqa: E402

if __name__ == "__main__":
    calistir()
