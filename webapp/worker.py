"""One bounded generation process per job; no uploaded filenames in commands."""
import json
import sys
from pathlib import Path
from webapp.generator import generate


def progress(percent, message):
    print(json.dumps(dict(progress=percent,message=message)),flush=True)


if __name__=='__main__':
    directory=Path(sys.argv[1])
    metadata=json.loads((directory/'job.json').read_text(encoding='utf-8'))
    try:
        generate(directory,metadata,progress)
    except Exception as error:
        print(json.dumps(dict(error=str(error) if isinstance(error,ValueError) else
                             'Die Verarbeitung ist fehlgeschlagen. Bitte eine andere MP3 versuchen.')),flush=True)
        sys.exit(1)
