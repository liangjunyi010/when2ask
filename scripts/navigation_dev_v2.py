"""Independent Navigation Dev v2 commands; live model calls require explicit --live."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask import nav2_study


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['oracle','prepare','check','ablation','episodes','report'])
    p.add_argument('--output-dir',default='outputs/navigation_dev_v2/study_v2');p.add_argument('--live',action='store_true')
    a=p.parse_args()
    if a.command in ('ablation','episodes') and not a.live:p.error('Paid model calls require --live')
    if a.command=='report':
        from when2ask.nav2_report import report
        report(Path(a.output_dir))
    else:getattr(nav2_study,a.command)(Path(a.output_dir))
