import argparse
import os
from webapp.app import Settings, create_app


def main():
    import uvicorn
    parser=argparse.ArgumentParser()
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8080)
    args=parser.parse_args()
    settings=Settings.environment()
    if args.host not in ('127.0.0.1','localhost','::1') and not settings.password:
        parser.error('Für Netzwerk-/Serverbetrieb SHOW_USERNAME und SHOW_PASSWORD setzen.')
    uvicorn.run(create_app(settings),host=args.host,port=args.port,workers=1,access_log=False)


if __name__=='__main__':
    main()
