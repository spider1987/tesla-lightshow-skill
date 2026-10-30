import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, ValidationError, Field
from typing import Literal

ROOT=Path(__file__).resolve().parents[1]


class Options(BaseModel):
    model_config=ConfigDict(extra='forbid')
    model: Literal['model_3','model_3_highland','model_y','model_s','model_x','cybertruck']='model_3'
    palette: Literal['neon','fire','halloween','ice']='neon'
    density: Literal['calm','balanced','intense']='balanced'
    bass_only: bool=True
    display: bool=True
    accents: bool=False
    mirrors: bool=False
    liftgate: bool=False
    liftgate_mode: Literal['start_end','dance']='start_end'
    charge_port: bool=False
    light_offset_ms: int=Field(default=500,ge=-2000,le=2000,multiple_of=20)


@dataclass
class Settings:
    data_dir: Path=ROOT/'runtime'/'jobs'
    max_upload_mb: int=50
    max_duration: int=600
    retention_hours: float=24
    max_jobs: int=3
    worker_timeout: int=900
    username: str=''
    password: str=''

    @classmethod
    def environment(cls):
        return cls(data_dir=Path(os.getenv('SHOW_DATA_DIR',str(ROOT/'runtime'/'jobs'))).resolve(),
                   max_upload_mb=int(os.getenv('SHOW_MAX_UPLOAD_MB','50')),
                   max_duration=int(os.getenv('SHOW_MAX_DURATION','600')),
                   retention_hours=float(os.getenv('SHOW_RETENTION_HOURS','24')),
                   max_jobs=int(os.getenv('SHOW_MAX_JOBS','3')),
                   worker_timeout=int(os.getenv('SHOW_WORKER_TIMEOUT','900')),
                   username=os.getenv('SHOW_USERNAME',''),password=os.getenv('SHOW_PASSWORD',''))


def safe_stem(filename):
    name=filename.replace('\\','/').rsplit('/',1)[-1]
    name=unicodedata.normalize('NFKC',Path(name).stem)
    name=re.sub(r'[^\w .,-]+','-',name,flags=re.UNICODE).strip(' .-')[:100].strip(' .')
    if not name or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        name='Meine-Lightshow'
    return name


def show_stem(filename,options):
    density={'calm':'Ruhig','balanced':'Ausgewogen','intense':'Intensiv'}[options.density]
    name=f'{safe_stem(filename)} - {density}'
    if options.liftgate:
        name+=' - Heckklappe-'+('Start-Ende' if options.liftgate_mode=='start_end' else 'Tanz')
    return name


class Jobs:
    def __init__(self,settings):
        self.settings=settings
        self.root=settings.data_dir.resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.entries={}
        self.slots=threading.BoundedSemaphore(settings.max_jobs)
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='lightshow')
        self.stopping=threading.Event()
        self.process=None
        for p in self.root.iterdir():
            if p.is_dir() and re.fullmatch('[a-f0-9]{32}',p.name):
                try:
                    job=json.loads((p/'job.json').read_text(encoding='utf-8'))
                    if job['status'] not in ('done','failed'):
                        job.update(status='failed',message='Verarbeitung durch Neustart beendet.')
                    self.entries[p.name]=job
                except (OSError,ValueError,KeyError):
                    # Unfinished upload left by a restart. It cannot be resumed.
                    shutil.rmtree(p)
        self.cleanup()
        self.janitor=threading.Thread(target=self.sweep,daemon=True)
        self.janitor.start()

    def path(self,id):
        if not re.fullmatch('[a-f0-9]{32}',id):
            raise HTTPException(404,'Show nicht gefunden.')
        p=(self.root/id).resolve()
        if p.parent!=self.root:
            raise HTTPException(404,'Show nicht gefunden.')
        return p

    def update(self,id,**changes):
        with self.lock:
            job=self.entries[id]
            job.update(changes)
            directory=self.path(id)
            temp=directory/'job.tmp'
            temp.write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
            temp.replace(directory/'job.json')

    def cleanup(self):
        with self.lock:
            for id,job in list(self.entries.items()):
                if job['status'] in ('done','failed') and time.time()-job['created']>self.settings.retention_hours*3600:
                    shutil.rmtree(self.path(id),ignore_errors=True)
                    del self.entries[id]

    def sweep(self):
        while not self.stopping.wait(60):
            self.cleanup()

    def run(self,id):
        directory=self.path(id)
        try:
            if self.stopping.is_set():
                raise ValueError('Verarbeitung durch Neustart beendet.')
            self.update(id,status='running',progress=8,message='Verarbeitung startet')
            with subprocess.Popen([sys.executable,'-m','webapp.worker',str(directory)],cwd=ROOT,
                                  stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as process:
                self.process=process
                if self.stopping.is_set():
                    process.kill()
                def read_progress():
                    for line in process.stdout:
                        try:
                            event=json.loads(line)
                            if 'error' in event:
                                self.update(id,message=event['error'])
                            elif 'progress' in event:
                                self.update(id,progress=event['progress'],message=event['message'])
                        except (ValueError,KeyError):
                            continue
                reader=threading.Thread(target=read_progress,daemon=True)
                reader.start()
                try:
                    code=process.wait(timeout=self.settings.worker_timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    reader.join()
                    raise ValueError('Zeitlimit erreicht. Bitte eine kürzere MP3 verwenden.')
                reader.join()
                if code or not (directory/'show.zip').exists():
                    raise ValueError(self.entries[id]['message'] if code else 'Das ZIP konnte nicht erstellt werden.')
                self.update(id,status='done',progress=100)
        except Exception as error:
            self.update(id,status='failed',message=str(error) if isinstance(error,ValueError) else 'Die Verarbeitung konnte nicht gestartet werden.')
            for name in ('input.mp3','analysis.wav','playback.mp3','sequence.fseq','show.zip','preview.json'):
                (directory/name).unlink(missing_ok=True)
        finally:
            self.process=None
            self.slots.release()

    def close(self):
        self.stopping.set()
        if self.process and self.process.poll() is None:
            self.process.kill()
        self.executor.shutdown(wait=True,cancel_futures=False)


def create_app(settings=None):
    settings=settings or Settings.environment()
    if bool(settings.username)!=bool(settings.password):
        raise ValueError('SHOW_USERNAME und SHOW_PASSWORD müssen gemeinsam gesetzt werden.')
    if min(settings.max_upload_mb,settings.max_duration,settings.max_jobs,settings.worker_timeout)<=0 or settings.retention_hours<=0:
        raise ValueError('Ungültige Serverlimits.')

    @asynccontextmanager
    async def lifespan(app):
        app.state.jobs=Jobs(settings)
        yield
        await asyncio.to_thread(app.state.jobs.close)

    app=FastAPI(title='Lightshow Studio',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware('http')
    async def protect(request,call_next):
        if settings.password and request.url.path!='/health':
            valid=False
            try:
                scheme,token=request.headers.get('authorization','').split(' ',1)
                user,password=base64.b64decode(token,validate=True).decode().split(':',1)
                valid=(scheme.lower()=='basic' and secrets.compare_digest(hashlib.sha256(user.encode()).digest(),hashlib.sha256(settings.username.encode()).digest())
                       and secrets.compare_digest(hashlib.sha256(password.encode()).digest(),hashlib.sha256(settings.password.encode()).digest()))
            except (ValueError,UnicodeError):
                pass
            if not valid:
                return JSONResponse({'detail':'Bitte anmelden.'},401,headers={'WWW-Authenticate':'Basic realm="Lightshow Studio", charset="UTF-8"'})
        admitted=False
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin and urlsplit(origin).netloc!=request.headers.get('host'):
                return JSONResponse({'detail':'Upload nur von dieser Oberfläche erlaubt.'},403)
            try:
                length=int(request.headers.get('content-length','0'))
            except ValueError:
                return JSONResponse({'detail':'Ungültige Uploadgröße.'},400)
            if length>settings.max_upload_mb*1024*1024+65536:
                return JSONResponse({'detail':f'Maximal {settings.max_upload_mb} MB pro MP3.'},413)
            original_receive=request._receive
            received=0
            async def limited_receive():
                nonlocal received
                try:
                    message=await asyncio.wait_for(original_receive(),timeout=30)
                except TimeoutError:
                    raise HTTPException(408,'Zeitlimit beim Upload erreicht.')
                received+=len(message.get('body',b''))
                if received>settings.max_upload_mb*1024*1024+65536:
                    raise HTTPException(413,'Upload ist zu groß.')
                return message
            request._receive=limited_receive
            if request.url.path=='/api/jobs':
                jobs=request.app.state.jobs
                jobs.cleanup()
                if not jobs.slots.acquire(blocking=False):
                    return JSONResponse({'detail':'Die Warteschlange ist voll. Bitte später erneut versuchen.'},429)
                request.state.upload_slot=True
                admitted=True
        try:
            response=await call_next(request)
        finally:
            if admitted and request.state.upload_slot:
                request.app.state.jobs.slots.release()
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get('/health')
    def health():
        return {'status':'ok'}

    @app.get('/api/config')
    def config():
        from webapp.generator import MODELS
        return dict(models=MODELS,max_upload_mb=settings.max_upload_mb,max_duration=settings.max_duration,
                    retention_hours=settings.retention_hours,authenticated=bool(settings.password))

    @app.post('/api/jobs',status_code=202)
    async def upload(request:Request,file:UploadFile=File(...),options:str=Form('{}')):
        try:
            parsed=Options.model_validate_json(options)
        except ValidationError:
            raise HTTPException(422,'Bitte gültige Effekteinstellungen auswählen.')
        if not (file.filename or '').lower().endswith('.mp3'):
            raise HTTPException(415,'Bitte eine MP3-Datei hochladen.')
        if parsed.accents and parsed.model not in ('model_3_highland','cybertruck'):
            raise HTTPException(422,'Dieses Modell hat keine unterstützten RGB-Ambientelichtsegmente.')
        jobs=request.app.state.jobs
        jobs.cleanup()
        id=secrets.token_hex(16)
        directory=jobs.path(id)
        directory.mkdir()
        try:
            size=0
            with (directory/'input.mp3').open('wb') as dest:
                while chunk:=await asyncio.wait_for(file.read(1024*1024),timeout=30):
                    size+=len(chunk)
                    if size>settings.max_upload_mb*1024*1024:
                        raise HTTPException(413,f'Maximal {settings.max_upload_mb} MB pro MP3.')
                    dest.write(chunk)
            if not size:
                raise HTTPException(400,'Die Datei ist leer.')
            job=dict(id=id,stem=show_stem(file.filename,parsed),options=parsed.model_dump(),created=time.time(),
                     status='queued',progress=4,message='In der Warteschlange',max_duration=settings.max_duration)
            with jobs.lock:
                jobs.entries[id]=job
            jobs.update(id)
            jobs.executor.submit(jobs.run,id)
            request.state.upload_slot=False
            return dict(id=id)
        except BaseException:
            with jobs.lock:
                jobs.entries.pop(id,None)
            shutil.rmtree(directory,ignore_errors=True)
            raise
        finally:
            await file.close()

    def get_job(request,id):
        jobs=request.app.state.jobs
        jobs.path(id)
        jobs.cleanup()
        with jobs.lock:
            if id not in jobs.entries:
                raise HTTPException(404,'Show nicht gefunden oder bereits abgelaufen.')
            return dict(jobs.entries[id])

    @app.get('/api/jobs/{id}')
    def status(request:Request,id:str):
        job=get_job(request,id)
        return {key:job[key] for key in ('id','stem','status','progress','message','created','options')}

    @app.get('/api/jobs/{id}/{asset}')
    def asset(request:Request,id:str,asset:str):
        job=get_job(request,id)
        if job['status']!='done':
            raise HTTPException(409,'Die Show ist noch nicht fertig.')
        assets={'download':('show.zip','application/zip'), 'preview':('preview.json','application/json'),
                'audio':('playback.mp3','audio/mpeg')}
        if asset not in assets:
            raise HTTPException(404,'Datei nicht gefunden.')
        name,mime=assets[asset]
        return FileResponse(request.app.state.jobs.path(id)/name,media_type=mime,
                            filename=job['stem']+'.zip' if asset=='download' else None)

    app.mount('/',StaticFiles(directory=ROOT/'webapp'/'static',html=True),name='studio')
    return app
