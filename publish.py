#!/usr/bin/env python3
"""Publish a new static daily dashboard and update the site pointer.
Usage: python publish.py /path/to/trading_dashboard_2026-11-12.html
"""
import datetime as dt, json, re, shutil, sys
from pathlib import Path
root=Path(__file__).resolve().parent
if len(sys.argv)!=2:
    raise SystemExit('Usage: python publish.py trading_dashboard_YYYY-MM-DD.html')
src=Path(sys.argv[1]).resolve()
m=re.fullmatch(r'trading_dashboard_(\d{4}-\d{2}-\d{2})\.html',src.name)
if not m or not src.is_file():
    raise SystemExit('Expected an existing trading_dashboard_YYYY-MM-DD.html file')
date=m.group(1)
dt.date.fromisoformat(date)
content=src.read_text(encoding='utf-8')
if '<html' not in content.lower() or '</html>' not in content.lower():
    raise SystemExit('Input does not look like a complete HTML document')
archive=root/'archive';archive.mkdir(exist_ok=True)
dest=archive/src.name
if dest.exists() and dest.resolve()!=src:
    raise SystemExit('An archive with this date already exists. Do not overwrite past briefs.')
if dest.resolve()!=src:shutil.copy2(src,dest)
manifest={'date':date,'file':f'archive/{src.name}','published_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'note':'Dated, static intelligence snapshot. Not live market data.'}
(root/'data'/'latest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Published',dest.relative_to(root),'— commit and push the changed files to deploy.')
