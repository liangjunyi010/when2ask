"""Local console and execution worker entry point (does not change frozen CLIs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'worker':
        from when2ask.console_worker import main
        main(sys.argv[2:])
    else:
        from when2ask.console_server import main
        main(sys.argv[1:])
