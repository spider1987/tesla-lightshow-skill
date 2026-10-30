"""Launch from the project root, with optional project-local test packages."""
import os
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
local=root/'.tools'/'python'
if local.exists():
    sys.path.insert(0,str(local))
    os.environ['PYTHONPATH']=str(local)+os.pathsep+os.environ.get('PYTHONPATH','')
os.environ['PYTHONIOENCODING']='utf-8'
from webapp.serve import main

if __name__=='__main__':
    main()
