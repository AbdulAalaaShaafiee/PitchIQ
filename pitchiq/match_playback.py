"""Browser-local video playback synchronized to a StatsBomb source event timeline.

The video is supplied by the user (local file, direct media URL, or embeddable
YouTube URL). The connector does not download, host, or bypass access controls
for copyrighted footage.
"""
from __future__ import annotations

import json
from typing import Any


def _safe_json(value: Any) -> str:
    """Serialize data for an inline script without allowing HTML/script breakout."""
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def build_player_html(events: list[dict[str, Any]], match_label: str) -> str:
    """Return the player/timeline UI; JavaScript keeps playback and event text in sync."""
    payload = _safe_json(events)
    label = _safe_json(str(match_label))
    return r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#101b2d;--border:#26364c;--muted:#9fb0c5;--text:#eef5ff;--accent:#52e0c2;--blue:#8bc7ff}
*{box-sizing:border-box}body{margin:0;background:transparent;color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
.shell{background:linear-gradient(135deg,#0c1524,#101b2d);border:1px solid var(--border);border-radius:18px;padding:16px;}
.head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px}.eyebrow{font-size:11px;letter-spacing:.16em;color:var(--accent);font-weight:800}.matchname{font-size:18px;font-weight:750;margin:4px 0}.hint{color:var(--muted);font-size:12px}
.grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.85fr);gap:14px}.panel{background:rgba(6,12,22,.55);border:1px solid var(--border);border-radius:13px;padding:12px;min-width:0}
.panel h3{margin:0 0 9px;font-size:14px}.sources{display:grid;gap:8px;margin-bottom:10px}.source-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.source-row input[type=url]{flex:1;min-width:200px}.filelabel{font-size:12px;color:var(--muted)}input,button{font:inherit}input[type=url],input[type=search],input[type=number]{background:#0a1423;color:var(--text);border:1px solid #334760;border-radius:8px;padding:8px 10px;min-width:0}input[type=file]{max-width:100%;font-size:12px;color:var(--muted)}button{background:#1d344b;border:1px solid #3a5875;border-radius:8px;padding:8px 10px;color:var(--text);font-weight:650;cursor:pointer}button:hover{border-color:var(--accent)}button:disabled{opacity:.45;cursor:not-allowed}.primary{background:#133b3b;border-color:#287f75;color:#cefff3}.video-wrap{position:relative;width:100%;aspect-ratio:16/9;background:#02060b;border-radius:10px;overflow:hidden}.video-wrap video,.video-wrap #youtubeContainer,.video-wrap #youtubePlayer{width:100%;height:100%;display:block;border:0}.video-wrap video{object-fit:contain}.video-wrap #youtubeContainer{display:none}.source-status{font-size:12px;color:var(--muted);min-height:18px;margin:7px 0}.offsets{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}.offset-field{display:grid;gap:4px;font-size:11px;color:var(--muted)}.offset-field input{width:100%}.active-card{border:1px solid #32675f;background:linear-gradient(140deg,rgba(25,90,80,.28),rgba(16,27,45,.9));border-radius:12px;padding:13px;min-height:180px}.active-kicker{font-size:10px;letter-spacing:.12em;color:var(--accent);font-weight:800}.active-title{font-size:19px;font-weight:800;margin:8px 0}.active-detail{font-size:14px;color:#dfebf9}.active-copy{font-size:14px;margin:9px 0}.meta{color:var(--muted);font-size:11px;overflow-wrap:anywhere}.next-line{border-top:1px solid var(--border);padding-top:10px;margin-top:11px;color:var(--muted);font-size:12px}.feed-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-top:12px}.feed{margin-top:8px;max-height:330px;overflow:auto;border:1px solid var(--border);border-radius:10px}.feedrow{display:grid;grid-template-columns:58px minmax(0,1fr);gap:8px;padding:8px 9px;border-bottom:1px solid #1b2a3d;background:#0b1423;width:100%;text-align:left;border-radius:0;font-weight:400}.feedrow:last-child{border-bottom:0}.feedrow.active{background:#173c3a;border-left:3px solid var(--accent)}.feedtime{color:var(--blue);font-size:11px;white-space:nowrap}.feedtitle{font-weight:700;font-size:12px}.feeddesc{font-size:11px;color:#b7c5d7;margin-top:2px;display:block}.badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.badge{font-size:10px;border:1px solid #33536c;background:#10243a;color:#bfe0ff;padding:3px 6px;border-radius:20px}.badge.imported{border-color:#28685d;color:#9df4db}.footer{font-size:11px;color:var(--muted);margin-top:10px}.help{border-left:2px solid #386d8e;padding-left:9px;margin:10px 0;color:var(--muted);font-size:11px}
@media(max-width:760px){.grid{grid-template-columns:1fr}.head{display:block}.offsets{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
</head>
<body>
<div class="shell">
 <div class="head"><div><div class="eyebrow">PITCHIQ · SYNCHRONIZED MATCH VIEW</div><div class="matchname" id="matchLabel"></div><div class="hint">Play a permitted video while the event explanation follows its timestamp.</div></div><div class="badge" id="sourceCount"></div></div>
 <div class="sources">
  <div class="source-row"><label class="filelabel" for="localVideo">Use a local video file</label><input id="localVideo" type="file" accept="video/*"></div>
  <div class="source-row"><input id="videoUrl" type="url" placeholder="YouTube link or direct MP4/WebM URL" aria-label="Video URL"><button class="primary" id="loadUrl">Load video link</button></div>
  <div class="help">StatsBomb provides event data, not match footage. Use a video you own or are authorized to view. This player does not download videos or bypass restrictions. Some YouTube videos cannot be embedded by their owners.</div>
 </div>
 <div class="grid">
  <section class="panel"><h3>Match playback</h3><div class="video-wrap"><video id="matchVideo" controls playsinline preload="metadata"></video><div id="youtubeContainer"><div id="youtubePlayer"></div></div></div><div class="source-status" id="sourceStatus">Choose a local video file or enter an embeddable video URL.</div><div class="feed-head"><strong>Video-to-match alignment</strong><span class="meta" id="clockStatus">Waiting for video</span></div><div class="offsets" id="offsetControls"></div><div class="help">Each offset is the position in the video where that period's source clock begins. Defaults assume a full recording with about 15 minutes of half-time; adjust them for edited clips or pre-roll.</div></section>
  <section class="panel"><h3>Event explanation · updates during playback</h3><div id="activeEvent" class="active-card"><div class="active-kicker">WAITING FOR PLAYBACK</div><div class="active-title">Load a video to begin</div><div class="active-detail">The current event will appear here when the video clock reaches its StatsBomb timestamp.</div></div><div class="badges"><span class="badge" id="mappedStatus">Timeline ready</span><span class="badge">Source timestamps</span><span class="badge">Rule-based explanation</span></div><div class="next-line" id="nextEvent">Press play. PitchIQ will track the latest event at or before the current video time.</div><div class="footer">Explanations summarize recorded event fields. They do not independently establish intent, tactical causation, or video identity.</div></section>
 </div>
 <div class="feed-head"><strong>Nearby event timeline</strong><input type="search" id="eventSearch" placeholder="Filter by team, player or event" aria-label="Filter event timeline"></div>
 <div class="hint" id="feedStatus">Choose an event to seek to its mapped video time.</div>
 <div class="feed" id="eventFeed" aria-live="polite"></div>
 <div class="footer">Source: StatsBomb Open Data event file. Event timing may need manual alignment because broadcast footage can include pre-roll, edits, or a different half-time interval.</div>
</div>
<script>
const SOURCE_EVENTS = __EVENTS__;
const MATCH_LABEL = __MATCH_LABEL__;
const matchLabelNode = document.getElementById('matchLabel');
matchLabelNode.textContent = MATCH_LABEL;
const eventCount = SOURCE_EVENTS.length;
document.getElementById('sourceCount').textContent = eventCount.toLocaleString() + ' source events';
const periodSet = [...new Set(SOURCE_EVENTS.map(e => Number(e.period)).filter(p => Number.isInteger(p) && p >= 1 && p <= 4))].sort((a,b)=>a-b);
const defaultOffsets = {1:0,2:3600,3:5400,4:6300};
const offsetControls = document.getElementById('offsetControls');
periodSet.forEach(period => {
 const label=document.createElement('label'); label.className='offset-field';
 const title=document.createElement('span'); title.textContent='Period '+period+' video start (seconds)';
 const input=document.createElement('input'); input.type='number'; input.min='0'; input.step='1'; input.id='periodOffset'+period; input.value=String(defaultOffsets[period] ?? 0);
 input.addEventListener('input', ()=>{mappedEvents=mapEvents();lastActive=-999;updateFromClock();});
 label.append(title,input); offsetControls.appendChild(label);
});
function escapeHtml(value){return String(value ?? '').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
function secLabel(value){if(!Number.isFinite(value)||value<0)return '—';const s=Math.floor(value);return String(Math.floor(s/3600)).padStart(2,'0')+':'+String(Math.floor((s%3600)/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function offsets(){const out={};periodSet.forEach(p=>{const node=document.getElementById('periodOffset'+p);out[p]=Math.max(0,Number(node?.value||0));});return out;}
function mapEvents(){const os=offsets();return SOURCE_EVENTS.map((event,index)=>({...event,_sourceIndex:index,video_time_seconds:os[Number(event.period)]+Number(event.timestamp_seconds)})).filter(e=>Number.isInteger(Number(e.period))&&Number.isFinite(Number(e.timestamp_seconds))&&Number.isFinite(e.video_time_seconds)).sort((a,b)=>a.video_time_seconds-b.video_time_seconds||a._sourceIndex-b._sourceIndex);}
let mappedEvents=mapEvents();
const video=document.getElementById('matchVideo'); const youtubeContainer=document.getElementById('youtubeContainer'); const sourceStatus=document.getElementById('sourceStatus');
let playerMode='none',ytPlayer=null,ytReady=false,ytPendingId=null,objectUrl=null,lastActive=-999,activeIndex=-1,sourceEventDuration=null;
const activeEventNode=document.getElementById('activeEvent'); const eventFeed=document.getElementById('eventFeed'); const nextEventNode=document.getElementById('nextEvent'); const searchNode=document.getElementById('eventSearch');
document.getElementById('mappedStatus').textContent=mappedEvents.length.toLocaleString()+' timestamped events';
function playerTime(){try{if(playerMode==='youtube'&&ytPlayer&&ytReady){const n=ytPlayer.getCurrentTime();return Number.isFinite(n)?n:NaN;}if(playerMode==='local'||playerMode==='url'){return Number.isFinite(video.currentTime)?video.currentTime:NaN;}}catch(e){}return NaN;}
function seekTo(seconds){if(!Number.isFinite(seconds)||seconds<0){sourceStatus.textContent='This event has no usable timestamp.';return;}try{if(playerMode==='youtube'&&ytPlayer&&ytReady){ytPlayer.seekTo(seconds,true);sourceStatus.textContent='Jumped to '+secLabel(seconds)+'.';}else if(playerMode==='local'||playerMode==='url'){video.currentTime=seconds;sourceStatus.textContent='Jumped to '+secLabel(seconds)+'.';video.focus();}else{sourceStatus.textContent='Load a video first, then select an event.';}}catch(e){sourceStatus.textContent='Could not seek to this event in the current video.';}}
function stopYoutube(){if(ytPlayer&&typeof ytPlayer.destroy==='function'){try{ytPlayer.destroy();}catch(e){}}ytPlayer=null;ytReady=false;youtubeContainer.innerHTML='<div id="youtubePlayer"></div>';}
function loadLocalFile(file){if(!file)return;stopYoutube();if(objectUrl){URL.revokeObjectURL(objectUrl);objectUrl=null;}objectUrl=URL.createObjectURL(file);playerMode='local';youtubeContainer.style.display='none';video.style.display='block';video.src=objectUrl;video.load();sourceStatus.textContent='Local video loaded in your browser: '+file.name+'.';lastActive=-999;}
function parseYoutubeId(url){try{const u=new URL(url);if(u.hostname==='youtu.be')return u.pathname.split('/').filter(Boolean)[0]||null;if(u.hostname.endsWith('youtube.com')||u.hostname.endsWith('youtube-nocookie.com')){if(u.searchParams.get('v'))return u.searchParams.get('v');const m=u.pathname.match(/\/(?:embed|shorts|live)\/([A-Za-z0-9_-]{11})/);return m?m[1]:null;}}catch(e){}return null;}
function loadYoutube(id){if(!/^[A-Za-z0-9_-]{11}$/.test(id)){sourceStatus.textContent='That YouTube URL does not contain a recognizable video ID.';return;}stopYoutube();playerMode='youtube';video.pause();video.removeAttribute('src');video.load();video.style.display='none';youtubeContainer.style.display='block';ytPendingId=id;sourceStatus.textContent='Loading YouTube player…';
 const createPlayer=()=>{if(!window.YT||!window.YT.Player||!ytPendingId)return;youtubeContainer.innerHTML='<div id="youtubePlayer"></div>';const wanted=ytPendingId;ytPlayer=new YT.Player('youtubePlayer',{width:'100%',height:'100%',videoId:wanted,playerVars:{playsinline:1,rel:0},events:{onReady:()=>{ytReady=true;sourceStatus.textContent='YouTube player ready. Press play to synchronize event commentary.';lastActive=-999;updateFromClock();},onError:(ev)=>{sourceStatus.textContent='YouTube could not embed this video (error '+ev.data+'). Try an authorized local file or direct MP4/WebM URL.';}}});};
 if(window.YT&&window.YT.Player){createPlayer();}else{window.onYouTubeIframeAPIReady=()=>createPlayer();let script=document.querySelector('script[data-pitchiq-youtube]');if(!script){script=document.createElement('script');script.src='https://www.youtube.com/iframe_api';script.dataset.pitchiqYoutube='1';script.onerror=()=>{sourceStatus.textContent='Could not load the YouTube player API. Try a local video or direct media URL.';};document.head.appendChild(script);}}
}
function loadUrl(){const value=document.getElementById('videoUrl').value.trim();if(!value){sourceStatus.textContent='Paste a YouTube link or direct MP4/WebM URL first.';return;}const ytId=parseYoutubeId(value);if(ytId){loadYoutube(ytId);return;}let parsed;try{parsed=new URL(value);}catch(e){sourceStatus.textContent='Enter a complete http(s) video URL.';return;}if(!['https:','http:'].includes(parsed.protocol)){sourceStatus.textContent='Only http(s) video URLs are supported.';return;}stopYoutube();playerMode='url';video.style.display='block';youtubeContainer.style.display='none';video.src=parsed.href;video.load();sourceStatus.textContent='Loading direct video URL. The host must permit browser playback.';lastActive=-999;}
document.getElementById('localVideo').addEventListener('change',e=>loadLocalFile(e.target.files&&e.target.files[0]));document.getElementById('loadUrl').addEventListener('click',loadUrl);document.getElementById('videoUrl').addEventListener('keydown',e=>{if(e.key==='Enter')loadUrl();});
function finishLabel(event){const t=String(event.event_type||'Event').replace(/\*/g,'').trim();const o=String(event.outcome||'').trim();return o?t+' · '+o:t;}
function currentIndexAt(seconds){if(!Number.isFinite(seconds))return -1;let idx=-1;for(let i=0;i<mappedEvents.length;i++){if(mappedEvents[i].video_time_seconds<=seconds+0.12)idx=i;else break;}return idx;}
function renderActive(index,seconds){if(index<0){activeEventNode.innerHTML='<div class="active-kicker">BEFORE FIRST TIMESTAMPED EVENT</div><div class="active-title">Waiting for the match to reach an event</div><div class="active-detail">When a timestamp is reached, its source event and explanation will appear here.</div>';nextEventNode.textContent=mappedEvents.length?'Next source event: '+mappedEvents[0].event_type+' · '+secLabel(mappedEvents[0].video_time_seconds):'No timestamped events available.';return;}
 const e=mappedEvents[index];const title=finishLabel(e);const imp=e.pitchiq_event_id!==null&&e.pitchiq_event_id!==undefined;activeEventNode.innerHTML='<div class="active-kicker">CURRENT SOURCE EVENT · PERIOD '+escapeHtml(e.period)+' · '+escapeHtml(e.timestamp||'timestamp unavailable')+'</div><div class="active-title">'+escapeHtml(e.team||'Team not supplied')+'</div><div class="active-detail">'+escapeHtml(e.player||'Player not supplied')+' · '+escapeHtml(title)+'</div><div class="active-copy">'+escapeHtml(e.explanation||'The source recorded this event but supplied no additional explanation.')+'</div><div class="badges"><span class="badge">Match minute '+escapeHtml(e.minute??'—')+'</span><span class="badge">Source ID '+escapeHtml(e.source_event_id||'not supplied')+'</span><span class="badge '+(imp?'imported':'')+'">'+(imp?'Included in PitchIQ analysis':'Timeline only · not mapped')+'</span></div><div class="meta" style="margin-top:8px">Video time '+secLabel(e.video_time_seconds)+' · event '+(index+1)+' of '+mappedEvents.length+'</div>';
 const next=mappedEvents[index+1];nextEventNode.textContent=next?'Next: '+(next.team?next.team+' · ':'')+next.event_type+' at '+String(next.timestamp||'source time')+' (video '+secLabel(next.video_time_seconds)+').':'This is the last timestamped event in the selected source timeline.';
}
function renderFeed(index){const query=searchNode.value.trim().toLowerCase();let selected=[];if(query){selected=mappedEvents.map((e,i)=>({...e,_mappedIndex:i})).filter(e=>(String(e.team||'')+' '+String(e.player||'')+' '+String(e.event_type||'')+' '+String(e.outcome||'')+' '+String(e.explanation||'')).toLowerCase().includes(query)).slice(0,80);}else{const start=Math.max(0,(index<0?0:index)-8);const end=Math.min(mappedEvents.length,start+24);selected=mappedEvents.slice(start,end).map((e,i)=>({...e,_mappedIndex:start+i}));}
 eventFeed.innerHTML='';if(!selected.length){eventFeed.innerHTML='<div class="feedrow">No events match this filter.</div>';return;}
 for(const e of selected){const b=document.createElement('button');b.type='button';b.className='feedrow'+(e._mappedIndex===index?' active':'');b.innerHTML='<span class="feedtime">'+escapeHtml(e.timestamp||'—')+'</span><span><span class="feedtitle">'+escapeHtml((e.team?e.team+' · ':'')+finishLabel(e))+'</span><span class="feeddesc">'+escapeHtml(e.explanation||'Source event')+'</span></span>';b.addEventListener('click',()=>seekTo(e.video_time_seconds));eventFeed.appendChild(b);}
 document.getElementById('feedStatus').textContent=(query?'Matching events (up to 80 shown): ':'Nearby events · ')+selected.length+' shown. Click an event to seek the video.';
}
function updateFromClock(){const seconds=playerTime();document.getElementById('clockStatus').textContent=Number.isFinite(seconds)?'Video '+secLabel(seconds):'Waiting for video';const index=currentIndexAt(seconds);if(index!==lastActive){lastActive=index;activeIndex=index;renderActive(index,seconds);renderFeed(index);}else if(index>=0){const e=mappedEvents[index];const time=activeEventNode.querySelector('.meta');if(time)time.textContent='Video time '+secLabel(e.video_time_seconds)+' · playback '+secLabel(seconds)+' · event '+(index+1)+' of '+mappedEvents.length;}}
searchNode.addEventListener('input',()=>renderFeed(activeIndex));
video.addEventListener('timeupdate',updateFromClock);video.addEventListener('seeked',updateFromClock);video.addEventListener('loadedmetadata',()=>{sourceStatus.textContent='Video ready · duration '+secLabel(video.duration)+'. Play to follow events.';updateFromClock();});video.addEventListener('error',()=>{if(playerMode==='url')sourceStatus.textContent='Browser could not play this URL. Use a direct video-file URL or a local video file, not an ordinary webpage URL.';});
renderFeed(-1);renderActive(-1,NaN);setInterval(updateFromClock,400);
</script>
</body>
</html>'''.replace("__EVENTS__", payload).replace("__MATCH_LABEL__", label)


def render_match_playback(events: list[dict[str, Any]], match_label: str = "Selected match") -> None:
    """Render a user-supplied video player with an auto-updating event timeline."""
    import streamlit as st
    import streamlit.components.v1 as components

    valid_events = [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []
    timestamped = sum(row.get("timestamp_seconds") is not None for row in valid_events)
    st.caption(
        f"Source timeline: {len(valid_events):,} events · {timestamped:,} with usable source timestamps. "
        "Event explanations update in the player as playback reaches each source timestamp."
    )
    if not valid_events:
        st.info("This match has no imported source-event timeline available for synchronized playback.")
        return
    components.html(build_player_html(valid_events, match_label), height=1120, scrolling=True)
