"""Narrate and caption the reviewed silent recording using local Kokoro assets."""
import argparse
import hashlib
import json
import os
import subprocess
import textwrap
from pathlib import Path
os.environ.setdefault('OMP_NUM_THREADS', '2')
import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro

def run(args):
    subprocess.run(args, check=True)

def stamp(seconds, ass=False):
    ms=round(seconds*(100 if ass else 1000))
    h,ms=divmod(ms,360000 if ass else 3600000)
    m,ms=divmod(ms,6000 if ass else 60000)
    s,ms=divmod(ms,100 if ass else 1000)
    return f'{h}:{m:02}:{s:02}.{ms:02}' if ass else f'{h:02}:{m:02}:{s:02},{ms:03}'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--tools',type=Path,required=True)
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); a.work.mkdir(parents=True,exist_ok=True)
    story=json.loads(Path(__file__).with_name('story.json').read_text())
    assert hashlib.sha256(a.source.read_bytes()).hexdigest()==story['source_sha256'], 'Unexpected source recording'
    options=ort.SessionOptions(); options.intra_op_num_threads=2; options.inter_op_num_threads=1
    session=ort.InferenceSession(str(a.tools/'kokoro-v1.0.onnx'),options,providers=['CPUExecutionProvider'])
    voice=Kokoro.from_session(session,str(a.tools/'voices-v1.0.bin'))
    rate=24000; duration=205.166667
    mixed=np.zeros(round(duration*rate),dtype=np.float32)
    cues=[]; report=[]
    for i,scene in enumerate(story['scenes']):
        audios=[]
        for j,line in enumerate(scene['lines']):
            wav=a.work/f'{i:02}-{j}.wav'
            cache_text=wav.with_suffix('.txt')
            if wav.exists() and cache_text.exists() and cache_text.read_text()==line: audio,sr=sf.read(wav,dtype='float32')
            else:
                audio,sr=voice.create(line,voice=story['voice'],speed=story['speed'],lang='en-us')
                sf.write(wav,audio,sr,subtype='PCM_16')
                cache_text.write_text(line)
            assert sr==rate
            audios.append(audio)
        gap=.20; raw=sum(len(x)/rate for x in audios)+gap*(len(audios)-1)
        available=scene['duration']-.65
        tempo=max(1,raw/available)
        if tempo>1.24: raise ValueError(f'Shorten scene {i}: {raw:.2f}s for {available:.2f}s')
        cursor=scene['at']+.25
        for j,(line,audio) in enumerate(zip(scene['lines'],audios)):
            if tempo>1:
                adjusted=a.work/f'{i:02}-{j}-fit.wav'
                run(['ffmpeg','-v','error','-y','-i',str(a.work/f'{i:02}-{j}.wav'),'-af',f'atempo={tempo}',str(adjusted)])
                audio,sr=sf.read(adjusted,dtype='float32')
            begin=round(cursor*rate); end=begin+len(audio)
            mixed[begin:end]=audio
            cues.append({'start':cursor,'end':end/rate,'text':line.replace('n eight n','n8n')})
            cursor=end/rate+gap/tempo
        assert cursor-gap/tempo<scene['at']+scene['duration']-.12
        report.append({'scene':i,'at':scene['at'],'speech_end':cursor-gap/tempo,'tempo':tempo})
        print(f'Narrated {i+1}/24; tempo {tempo:.3f}',flush=True)
    sf.write(a.work/'voice.wav',mixed,rate,subtype='PCM_16')
    run(['ffmpeg','-v','error','-y','-i',str(a.work/'voice.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-ar','48000',str(a.work/'voice-master.wav')])
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,28,&H00FFFFFF,&H00FFFFFF,&H0023140B,&H0023140B,0,0,0,0,100,100,0,0,1,1,0,2,160,160,16,1
Style: Heading,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H0023140B,&H0023140B,-1,0,0,0,100,100,0,0,1,0,0,7,96,96,18,1
Style: Phase,DejaVu Sans,22,&H00BDDF52,&H00BDDF52,&H0023140B,&H0023140B,-1,0,0,0,100,100,1,0,1,0,0,9,96,96,20,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events=[]
    def event(start,end,style,text,layer=1):
        events.append(f'Dialogue: {layer},{stamp(start,True)},{stamp(end,True)},{style},,0,0,0,,{text}')
    for scene in story['scenes']:
        start=scene['at']; end=start+scene['duration']
        event(start,end,'Heading',r'{\fad(180,120)}'+scene['title'])
        event(start,end,'Phase',r'{\move(2070,20,1824,20,0,420)\fad(180,160)}'+scene['phase'])
    event(0,duration,'Heading',r'{\an7\pos(0,0)\p1\bord0\1c&HBDDF52&\clip(96,966,96,970)\t(0,205167,\clip(96,966,1824,970))}m 96 966 l 1824 966 1824 970 96 970',0)
    srt=[]
    for i,cue in enumerate(cues,1):
        wrapped=textwrap.wrap(cue['text'],width=92)
        assert len(wrapped)<=2
        event(cue['start'],cue['end']+.08,'Caption',r'{\fad(70,70)\pos(960,1058)}'+r'\N'.join(wrapped))
        srt.append(f"{i}\n{stamp(cue['start'])} --> {stamp(cue['end']+.08)}\n"+'\n'.join(wrapped)+'\n')
    (a.work/'edit.ass').write_text(header+'\n'.join(events)+'\n')
    (a.work/'RelayCart-End-to-End-Demo.en.srt').write_text('\n'.join(srt))
    (a.work/'timing-review.json').write_text(json.dumps({'voice':story['voice'],'scenes':report,'captions':cues},indent=2)+'\n')
    vf=f'scale=1728:972:flags=lanczos,pad=1920:1080:96:0:color=0x0b1423,drawbox=x=0:y=0:w=1920:h=64:color=0x0b1423:t=fill,ass={a.work}/edit.ass'
    run(['ffmpeg','-v','warning','-y','-i',str(a.source),'-i',str(a.work/'voice-master.wav'),'-i',str(a.work/'RelayCart-End-to-End-Demo.en.srt'),'-map','0:v:0','-map','1:a:0','-map','2:s:0','-map_chapters','0','-map_metadata','0','-vf',vf,'-c:v','libx264','-preset','fast','-crf','18','-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-c:s','mov_text','-metadata:s:a:0','language=eng','-metadata:s:s:0','language=eng','-metadata:s:s:0','title=English narration','-disposition:s:0','0','-metadata','comment=Recorded synthetic demo. Male synthetic narration; burned-in English captions and optional subtitle track. Animated editorial headings; original UI evidence preserved.','-movflags','+faststart','-t',str(duration),str(a.output)])

if __name__=='__main__': main()
