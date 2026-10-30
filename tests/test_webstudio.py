import io
import json
import os
from pathlib import Path
import struct
import tempfile
import time
import unittest
from unittest.mock import patch
import wave
import zipfile

import numpy as np
from fastapi.testclient import TestClient
from webapp.app import Settings,create_app,safe_stem
from webapp.generator import compose_analysis,convert,validate_sequence
from analyze_audio import analyze,load_wav_stereo


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=tempfile.TemporaryDirectory()
        cls.wav=Path(cls.source.name)/'test.wav'
        rate=44100
        t=np.arange(rate*6)/rate
        beat=(t%.45)
        signal=(.45*np.sin(2*np.pi*70*t)*np.exp(-beat*18)
                +.16*np.sin(2*np.pi*900*t)*(np.sin(2*np.pi*2.2*t)**2)
                +.05*np.sin(2*np.pi*6500*t)*np.exp(-(t%.22)*60))
        stereo=np.column_stack((signal,signal*.9))
        with wave.open(str(cls.wav),'wb') as dest:
            dest.setnchannels(2);dest.setsampwidth(2);dest.setframerate(rate)
            dest.writeframes((stereo*32767).astype('<i2').tobytes())
        cls.mp3=Path(cls.source.name)/'test.mp3'
        convert(['-i',str(cls.wav),'-ar','44100','-c:a','libmp3lame',str(cls.mp3)])
        left,right,sr=load_wav_stereo(cls.wav)
        cls.analysis=analyze(left,right,sr)

    @classmethod
    def tearDownClass(cls):
        cls.source.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.settings=Settings(data_dir=Path(self.temp.name)/'jobs',max_duration=20,worker_timeout=90)
        self.app=create_app(self.settings)
        self.client=TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.temp.cleanup()

    def wait_job(self,id):
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            result=self.client.get('/api/jobs/'+id)
            self.assertEqual(result.status_code,200)
            job=result.json()
            if job['status'] in ('done','failed'):
                return job
            time.sleep(.1)
        self.fail('Job timed out')

    def upload(self,data=None,options=None,name='Mein Song.mp3'):
        return self.client.post('/api/jobs',files={'file':(name,data or self.mp3.read_bytes(),'audio/mpeg')},
                                data={'options':json.dumps(options or {})})

    def test_real_upload_worker_zip_and_preview(self):
        result=self.upload(options={'model':'model_3','density':'balanced','palette':'fire'})
        self.assertEqual(result.status_code,202,result.text)
        id=result.json()['id']
        early=self.client.get(f'/api/jobs/{id}/download')
        self.assertIn(early.status_code,(409,200))
        job=self.wait_job(id)
        self.assertEqual(job['status'],'done',job)
        download=self.client.get(f'/api/jobs/{id}/download')
        self.assertEqual(download.status_code,200)
        with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
            self.assertEqual(sorted(archive.namelist()),['Mein Song - Ausgewogen.fseq','Mein Song - Ausgewogen.mp3'])
            self.assertIsNone(archive.testzip())
            sequence=archive.read('Mein Song - Ausgewogen.fseq')
            self.assertEqual(sequence[:4],b'PSEQ')
            self.assertEqual(struct.unpack_from('<I',sequence,10)[0],200)
            offset=struct.unpack_from('<H',sequence,4)[0]
            values=np.frombuffer(sequence,np.uint8,offset=offset).reshape(-1,200)
            self.assertFalse(values[:,30:46].any(),'All movement disabled by default')
            self.assertTrue(values[:,:4].any(),'Bass drives main beams')
            self.assertTrue(values[:,175:178].any(),'RGB display enabled')
        preview=self.client.get(f'/api/jobs/{id}/preview').json()
        self.assertEqual(len(preview['tracks']),10)
        self.assertEqual(preview['model'],'Model 3 · vor 2024')
        self.assertGreater(len(preview['colors']),0)
        self.assertEqual(self.client.get(f'/api/jobs/{id}/audio').status_code,200)
        self.assertEqual(self.client.get(f'/api/jobs/{id}/audio',headers={'Range':'bytes=0-100'}).status_code,206)
        self.assertFalse((self.settings.data_dir/id/'input.mp3').exists())
        self.assertFalse((self.settings.data_dir/id/'analysis.wav').exists())
        self.assertIn('Ausgewogen.zip',download.headers['content-disposition'])

    def test_density_names_and_liftgate_schedule(self):
        from webapp.app import Options,show_stem
        from webapp.generator import schedule_liftgate
        from fseq_writer import FseqWriter
        for key,label in [('calm','Ruhig'),('balanced','Ausgewogen'),('intense','Intensiv')]:
            self.assertEqual(show_stem('Song.mp3',Options(density=key)),f'Song - {label}')
        writer=FseqWriter(200,1500,20)
        writer.set_range(300,400,41,128) # previous dance must be removed
        schedule_liftgate(writer)
        values=np.frombuffer(writer.frames,np.uint8).reshape(-1,200)[:,40]
        self.assertTrue(np.all(values[:15]==64))
        self.assertFalse(values[15:1300].any())
        self.assertTrue(np.all(values[1300:1315]==191))
        self.assertFalse(values[1315:].any())
        self.assertNotIn(128,values)
        with self.assertRaisesRegex(ValueError,'19 Sekunden'):
            schedule_liftgate(FseqWriter(200,300,20))
        self.assertEqual(show_stem('Song.mp3',Options(liftgate=True)),'Song - Ausgewogen - Heckklappe-Start-Ende')
        self.assertEqual(show_stem('Song.mp3',Options(liftgate=True,liftgate_mode='dance')),'Song - Ausgewogen - Heckklappe-Tanz')
        # Long enough analysis for the real composer to pre-open and dance.
        extended=dict(self.analysis)
        original_n=self.analysis['n_frames']
        for key,values in self.analysis.items():
            if isinstance(values,list) and len(values)==original_n:
                extended[key]=values*10
        extended['n_frames']=original_n*10
        for key in ('beat_frames','strong_beat_frames','onset_frames','drop_frames'):
            extended[key]=[f+i*original_n for i in range(10) for f in self.analysis.get(key,[])]
        extended['onset_strength']=self.analysis.get('onset_strength',[])*10
        extended['tempo_change_points']=[]
        fixed=compose_analysis(extended,Options(liftgate=True).model_dump())
        dance=compose_analysis(extended,Options(liftgate=True,liftgate_mode='dance').model_dump())
        fixed_values=np.frombuffer(fixed.frames,np.uint8).reshape(-1,200)[:,40]
        dance_values=np.frombuffer(dance.frames,np.uint8).reshape(-1,200)[:,40]
        self.assertNotIn(128,fixed_values)
        self.assertIn(128,dance_values)
        self.assertEqual(fixed_values[0],64)
        self.assertIn(191,fixed_values[-200:])
        for name,result in [('fixed',fixed),('dance',dance)]:
            result.save(Path(self.temp.name)/(name+'.fseq'))
            validate_sequence(Path(self.temp.name)/(name+'.fseq'),70)

    def test_bad_file_fails_and_releases_queue(self):
        result=self.upload(b'this is not mp3')
        self.assertEqual(result.status_code,202)
        job=self.wait_job(result.json()['id'])
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/download").status_code,409)
        for _ in range(self.settings.max_jobs):
            self.assertTrue(self.app.state.jobs.slots.acquire(blocking=False))
        for _ in range(self.settings.max_jobs):self.app.state.jobs.slots.release()

    def test_invalid_options_and_non_mp3(self):
        self.assertEqual(self.upload(options={'model':'invented'}).status_code,422)
        self.assertEqual(self.upload(options={'accents':True}).status_code,422)
        self.assertEqual(self.upload(name='test.wav').status_code,415)
        self.assertEqual(self.client.get('/api/jobs/../../etc/passwd').status_code,404)
        self.assertEqual(self.client.get('/api/jobs/'+'a'*32).status_code,404)

    def test_upload_limit_and_cross_origin(self):
        self.settings.max_upload_mb=1
        result=self.upload(b'x'*(1024*1024+70000))
        self.assertEqual(result.status_code,413)
        self.assertEqual(self.client.post('/api/jobs',headers={'Origin':'https://other.example'}).status_code,403)
        # Unknown body length is also bounded, not just Content-Length.
        body=b'x'*(1024*1024+70000)
        result=self.client.post('/api/jobs',content=iter([body]),headers={'Content-Type':'multipart/form-data; boundary=x'})
        self.assertIn(result.status_code,(400,413))

    def test_full_queue_rejected_before_upload(self):
        jobs=self.app.state.jobs
        for _ in range(self.settings.max_jobs):self.assertTrue(jobs.slots.acquire(False))
        self.assertEqual(self.upload().status_code,429)
        for _ in range(self.settings.max_jobs):jobs.slots.release()

    def test_expiration_and_safe_names(self):
        self.assertEqual(safe_stem('../../CON.mp3'),'Meine-Lightshow')
        self.assertNotIn('/',safe_stem('../My <Song>.mp3'))
        jobs=self.app.state.jobs
        id='b'*32
        jobs.path(id).mkdir()
        jobs.entries[id]=dict(id=id,created=0,status='done')
        jobs.cleanup()
        self.assertFalse(jobs.path(id).exists())
        self.assertEqual(self.client.get('/api/jobs/'+id).status_code,404)

    def test_authentication(self):
        settings=Settings(data_dir=Path(self.temp.name)/'auth',username='tester',password='only-a-test-password')
        with TestClient(create_app(settings)) as client:
            self.assertEqual(client.get('/').status_code,401)
            self.assertEqual(client.get('/health').status_code,200)
            self.assertEqual(client.get('/api/config',auth=('tester','wrong')).status_code,401)
            self.assertEqual(client.get('/api/config',auth=('tester','only-a-test-password')).status_code,200)
            self.assertEqual(client.get('/api/config',headers={'Authorization':'Basic broken'}).status_code,401)

    def test_frontend_served_with_security_headers(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn('Lightshow Studio',response.text)
        self.assertIn("frame-ancestors 'none'",response.headers['content-security-policy'])
        self.assertEqual(self.client.get('/studio.js').status_code,200)

    def test_all_models_and_effect_controls(self):
        from webapp.app import Options
        for model in ('model_3','model_3_highland','model_s','model_x','model_y','cybertruck'):
            with self.subTest(model=model):
                options=Options(model=model).model_dump()
                result=compose_analysis(self.analysis,options)
                arr=np.frombuffer(result.frames,np.uint8).reshape(-1,200)
                self.assertFalse(arr[:,30:46].any())
                self.assertTrue(arr[:,175:178].any())
                self.assertFalse(arr[:,178:193].any(),'Accent switch off must silence all five segments')
                if model not in ('cybertruck',):self.assertFalse(arr[:,46:175].any())
                result.save(Path(self.temp.name)/'test.fseq')
                validate_sequence(Path(self.temp.name)/'test.fseq',20)
        calm=compose_analysis(self.analysis,Options(density='calm').model_dump())
        intense=compose_analysis(self.analysis,Options(density='intense').model_dump())
        self.assertNotEqual(calm.frames,intense.frames)
        off=compose_analysis(self.analysis,Options(display=False).model_dump())
        arr=np.frombuffer(off.frames,np.uint8).reshape(-1,200)
        self.assertFalse(arr[:,175:178].any())
        highland=compose_analysis(self.analysis,Options(model='model_3_highland',accents=True).model_dump())
        arr=np.frombuffer(highland.frames,np.uint8).reshape(-1,200)
        self.assertTrue(arr[:,178:193].any())

    def test_duration_limit_and_empty_upload(self):
        self.assertEqual(self.client.post('/api/jobs',files={'file':('empty.mp3',b'','audio/mpeg')}).status_code,400)
        self.settings.max_duration=3
        result=self.upload()
        self.assertEqual(result.status_code,202)
        job=self.wait_job(result.json()['id'])
        self.assertEqual(job['status'],'failed')
        self.assertIn('Sekunden',job['message'])

    def test_light_offset_directions_and_motion_preservation(self):
        from webapp.generator import shift_lights
        from fseq_writer import FseqWriter
        for offset,expected in [(500,65),(-500,15),(0,40)]:
            writer=FseqWriter(200,150,20)
            writer.set(40,1,255)
            writer.set(40,176,123)
            writer.set(0,41,64)
            writer.set(100,41,191)
            shift_lights(writer,offset)
            arr=np.frombuffer(writer.frames,np.uint8).reshape(-1,200)
            self.assertEqual(np.flatnonzero(arr[:,0]).tolist(),[expected])
            self.assertEqual(arr[expected,175],123)
            self.assertEqual(arr[0,40],64)
            self.assertEqual(arr[100,40],191)
            self.assertEqual(writer.frame_count,150)
        self.assertEqual(self.upload(options={'light_offset_ms':2100}).status_code,422)
        self.assertEqual(self.upload(options={'light_offset_ms':501}).status_code,422)

    def test_completed_job_survives_restart(self):
        settings=Settings(data_dir=Path(self.temp.name)/'restart')
        id='c'*32
        directory=settings.data_dir/id
        directory.mkdir(parents=True)
        job=dict(id=id,stem='Song',options={},created=time.time(),status='done',progress=100,message='Fertig')
        (directory/'job.json').write_text(json.dumps(job))
        with TestClient(create_app(settings)) as client:
            self.assertEqual(client.get('/api/jobs/'+id).json()['status'],'done')


if __name__=='__main__':unittest.main()
