"""World Cup 2026 Final highlight playback with manually mapped moments.

The event notes are based on the official FIFA match report. Because a highlights
montage is edited and is not a full-match event feed, video offsets are mapped by
the user while watching the clip rather than invented from match-minute values.
"""
from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse
from typing import Any

FINAL_VIDEO_URL = "https://www.youtube.com/watch?v=6HaHNYjnghE"
FINAL_VIDEO_ID = "6HaHNYjnghE"
FIFA_REPORT_URL = (
    "https://www.fifa.com/en/tournaments/mens/worldcup/"
    "canadamexicousa2026/articles/spain-argentina-final-report-highlights"
)

KEY_MOMENTS: list[dict[str, Any]] = [
    {
        "id": "argentina-saves",
        "title": "Argentina's goalkeeper keeps the match alive",
        "match_time": "Exact minute not specified in the report",
        "team": "Argentina",
        "player": "Emiliano Martínez",
        "event_type": "Goalkeeper saves",
        "explanation": (
            "FIFA's final report says Emiliano Martínez made a series of saves "
            "to thwart Spain. The report does not provide exact match minutes "
            "for those saves, so this moment must be mapped to the matching clip manually."
        ),
    },
    {
        "id": "winning-goal",
        "title": "Spain's winning-goal sequence",
        "match_time": "106′ (extra time)",
        "team": "Spain",
        "player": "Pedro Porro · Nico Williams · Ferran Torres",
        "event_type": "Goal",
        "explanation": (
            "In the 106th minute of extra time, FIFA's report says Pedro Porro delivered "
            "the cross, Nico Williams nodded the ball down at the far post, and Ferran "
            "Torres finished first-time into the roof of the net. This was the goal that "
            "made the score 1–0."
        ),
    },
    {
        "id": "final-result",
        "title": "Spain win the World Cup Final",
        "match_time": "After extra time",
        "team": "Spain",
        "player": "Spain national team",
        "event_type": "Final result",
        "explanation": (
            "FIFA records Spain's 1–0 victory over Argentina after extra time in the "
            "2026 FIFA World Cup Final. This is the match result, not a claim that the "
            "highlight video contains every event from the full match."
        ),
    },
]


def parse_youtube_video_id(value: str) -> str | None:
    """Extract a standard YouTube video ID from a URL, otherwise return None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        if parsed.path.rstrip("/") == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.match(r"^/(?:embed|shorts|live)/([A-Za-z0-9_-]{11})(?:/|$)", parsed.path)
            candidate = match.group(1) if match else ""
    else:
        return None
    return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate or "") else None


def get_key_moments() -> list[dict[str, Any]]:
    """Return copies of the supported curated match moments."""
    return [dict(moment) for moment in KEY_MOMENTS]


def build_world_cup_final_html(video_id: str = FINAL_VIDEO_ID) -> str:
    """Build an interactive YouTube player and manually mappable moment timeline."""
    valid_id = video_id if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id or "") else FINAL_VIDEO_ID
    video_id_json = json.dumps(valid_id)
    moments_json = json.dumps(get_key_moments(), ensure_ascii=False).replace("</", "<\\/")
    html = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:dark;--bg:#0a1220;--panel:#101d30;--line:#263a54;--text:#edf4ff;--muted:#9fb0c8;--mint:#69ead0;--blue:#8bc6ff;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 Inter,Segoe UI,Arial,sans-serif}button{cursor:pointer;font:inherit}.shell{padding:16px;max-width:1240px;margin:auto}.eyebrow{color:var(--mint);letter-spacing:.12em;font-size:11px;font-weight:800}.head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:14px}.head h1{font-size:23px;line-height:1.2;margin:5px 0 6px}.muted{color:var(--muted)}.pill{border:1px solid var(--line);color:var(--blue);border-radius:999px;padding:4px 9px;white-space:nowrap;font-size:11px}.cols{display:grid;grid-template-columns:minmax(0,1.18fr) minmax(300px,.82fr);gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}.panelhead{padding:13px 15px;border-bottom:1px solid var(--line);font-weight:750}.vidbox{background:#03070e;position:relative;aspect-ratio:16/9;width:100%;min-height:180px}.vidbox iframe,.vidbox #ytMount{width:100%;height:100%;position:absolute;inset:0;border:0}.status{padding:10px 14px;color:var(--muted);font-size:12px;border-bottom:1px solid var(--line)}.mapping-note{padding:13px 14px;color:var(--muted);font-size:12px}.moment{padding:13px 14px;border-bottom:1px solid var(--line)}.moment:last-child{border-bottom:0}.moment.active{background:#13342f;box-shadow:inset 3px 0 var(--mint)}.momenttop{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}.moment h3{font-size:14px;margin:0 0 4px}.game-time{color:var(--mint);font-size:12px;font-weight:750;white-space:nowrap}.copy{color:#d4dfef;margin:9px 0}.source{font-size:11px;color:var(--muted)}.moment-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.btn{border:1px solid #38516c;background:#182940;color:var(--text);border-radius:8px;padding:7px 10px;font-size:12px}.btn.primary{background:#144e48;border-color:#2e8e80;color:#e7fffa}.btn:disabled{opacity:.45;cursor:not-allowed}.mapped{display:inline-block;font-size:11px;padding:3px 7px;border-radius:999px;border:1px solid #3e6d67;color:var(--mint)}.unmapped{display:inline-block;font-size:11px;padding:3px 7px;border-radius:999px;border:1px solid #6d5837;color:#f3d39b}.activebox{padding:14px}.activebox .label{font-size:11px;color:var(--mint);font-weight:800;letter-spacing:.08em}.activebox h2{font-size:20px;margin:8px 0}.activebox p{color:#d4dfef}.timeline-status{padding:10px 14px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}.manual-fallback{margin:12px 14px;padding:13px;border:1px solid #8b6735;border-radius:10px;background:#251e13;color:#f3e5c9}.manual-fallback p{margin:7px 0;color:#d7c8ac;font-size:12px}.manual-fallback label{display:block;font-size:12px;font-weight:700;margin:10px 0 5px}.manual-time-row{display:flex;gap:7px;flex-wrap:wrap}.manual-fallback input{background:#0a1220;color:var(--text);border:1px solid #6e604a;border-radius:7px;padding:8px;min-width:140px;flex:1;font:inherit}.manual-fallback .note{font-size:11px;color:#c9b996;margin-top:7px}.footer{margin-top:14px;color:var(--muted);font-size:11px}.footer a{color:var(--blue)}.key{font-size:11px;color:var(--muted)}@media(max-width:750px){.cols{grid-template-columns:1fr}.head h1{font-size:20px}.shell{padding:10px}}
</style>
</head><body>
<div class="shell">
  <div class="head"><div><div class="eyebrow">PITCHIQ · WORLD CUP FINAL DEMO</div><h1>Spain vs Argentina · 2026 Final</h1><div class="muted">Official FIFA highlights with synchronized, source-grounded explanations</div></div><span class="pill">Curated highlight moments</span></div>
  <div class="cols">
    <section class="panel">
      <div class="panelhead">Match video</div>
      <div class="vidbox"><div id="ytMount"></div></div>
      <div class="status" id="videoStatus">Loading the official FIFA YouTube player…</div>
      <div class="manual-fallback" id="manualFallback" style="display:none">
        <strong>YouTube allows playback on its site, but blocks embedding here.</strong>
        <p>Open the official video in YouTube. When a curated moment appears, pause the video and enter the clip timestamp displayed by YouTube.</p>
        <label for="manualVideoTime">Current YouTube clip time (MM:SS or seconds)</label>
        <div class="manual-time-row"><input id="manualVideoTime" type="text" inputmode="numeric" placeholder="e.g. 02:34 or 154"><button class="btn primary" id="previewExternalTime">Update explanation from this time</button></div>
        <div class="note">Because the video is playing on a separate YouTube page, the browser cannot read its playback clock or control seeking from PitchIQ. Enter the visible time manually; mapped explanations can then be previewed on PitchIQ's timeline.</div>
      </div>
      <div class="mapping-note"><strong>How synchronization works:</strong> this is an edited highlights video, not a continuous full-match feed. If the embedded player works, map the current video time when a moment appears. If YouTube blocks embedding, open the video on YouTube and enter its displayed timestamp in the manual fallback box. Match minutes are kept separate from video seconds.</div>
      <div class="moment-actions" style="padding:0 14px 14px"><button class="btn" id="resetMappings">Reset moment mappings</button><button class="btn" id="openYoutube">Open video on YouTube ↗</button></div>
    </section>
    <section class="panel">
      <div class="panelhead">Current explanation</div>
      <div id="activeMoment" class="activebox"><div class="label">WAITING FOR A MAPPED MOMENT</div><h2>Play the highlights</h2><p>Map the moments below while they are visible in the video. The matching explanation will become active automatically during playback.</p></div>
      <div class="timeline-status" id="playbackClock">Video time: —</div>
      <div class="panelhead">Curated key moments</div>
      <div id="momentList"></div>
    </section>
  </div>
  <div class="footer">Source: <a href="__REPORT_URL__" target="_blank" rel="noopener">FIFA official final report and highlights</a>. Key-match facts are based on FIFA's report; the manually mapped video offsets are user-set editorial timings, not official event timestamps. This highlights timeline is not a complete event-by-event feed of the 120-minute match. Video availability and embedding are controlled by YouTube/FIFA.</div>
</div>
<script>
const VIDEO_ID = __VIDEO_ID__;
const MOMENTS = __MOMENTS__;
const STORAGE_KEY = 'pitchiq-world-cup-2026-final-moment-offsets-v1-' + VIDEO_ID;
let player=null, playerReady=false, manualMode=false, mapping={}, activeMomentId=null, videoError=null;
const statusNode=document.getElementById('videoStatus');
const listNode=document.getElementById('momentList');
const activeNode=document.getElementById('activeMoment');
const clockNode=document.getElementById('playbackClock');
const fallbackNode=document.getElementById('manualFallback');
const manualTimeNode=document.getElementById('manualVideoTime');
function safeLoad(){try{const raw=localStorage.getItem(STORAGE_KEY);const parsed=raw?JSON.parse(raw):{};if(parsed&&typeof parsed==='object')mapping=parsed;}catch(e){mapping={};}}
function safeSave(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(mapping));}catch(e){/* in-memory mappings still work for this open page */}}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function secLabel(n){if(!Number.isFinite(n)||n<0)return '—';const x=Math.floor(n);return Math.floor(x/60)+':'+String(x%60).padStart(2,'0');}
function parseManualSeconds(){
  if(!manualTimeNode)return NaN;
  const raw=manualTimeNode.value.trim();
  if(!raw)return NaN;
  if(/^\d+(?:\.\d+)?$/.test(raw)){const n=Number(raw);return Number.isFinite(n)&&n>=0?n:NaN;}
  const parts=raw.split(':');
  if(parts.length!==2&&parts.length!==3)return NaN;
  if(parts.some(part=>!/^\d{1,2}$/.test(part)))return NaN;
  const nums=parts.map(Number);
  const secs=nums[nums.length-1];
  const mins=nums[nums.length-2];
  if(secs>=60||(parts.length===3&&mins>=60))return NaN;
  return parts.length===2?mins*60+secs:nums[0]*3600+mins*60+secs;
}
function currentSeconds(){
  if(manualMode)return parseManualSeconds();
  try{return playerReady?Number(player.getCurrentTime()):NaN;}catch(e){return NaN;}
}
function enableManualFallback(errorCode, reason=''){
  manualMode=true;playerReady=false;videoError=errorCode;
  const mount=document.getElementById('ytMount');
  if(mount)mount.style.display='none';
  const videoBox=document.querySelector('.vidbox');if(videoBox)videoBox.style.display='none';
  fallbackNode.style.display='block';
  if(errorCode===101||errorCode===150){
    statusNode.textContent='YouTube embed error '+errorCode+': this video cannot be played inside PitchIQ. Manual timestamp mode is ready.';
  }else{
    statusNode.textContent=(reason||('YouTube embed error '+(errorCode??'unknown')+'.'))+' Manual timestamp mode is ready; open the video on YouTube.';
  }
  renderMoments();
}
function previewManualTime(){
  if(!manualMode)return;
  const now=parseManualSeconds();
  if(!Number.isFinite(now)){
    statusNode.textContent='Enter a valid clip timestamp such as 02:34, 1:02:34, or 154 seconds.';
    return;
  }
  updateActive();
  statusNode.textContent='Previewing mapped explanations at clip time '+secLabel(now)+'. This does not seek or control the separate YouTube tab.';
}
function renderMoments(){listNode.innerHTML='';for(const m of MOMENTS){const v=Number(mapping[m.id]);const isMapped=Number.isFinite(v)&&v>=0;const isActive=activeMomentId===m.id;const el=document.createElement('article');el.className='moment'+(isActive?' active':'');el.innerHTML=`<div class="momenttop"><div><h3>${esc(m.title)}</h3><div class="key">${esc(m.team)} · ${esc(m.player)}</div></div><div class="game-time">${esc(m.match_time)}</div></div><div class="copy">${esc(m.explanation)}</div><div>${isMapped?`<span class="mapped">Mapped to video ${secLabel(v)}</span>`:`<span class="unmapped">Not mapped to video</span>`}</div><div class="moment-actions"><button class="btn primary" data-map="${esc(m.id)}" ${(playerReady||manualMode)?'':'disabled'}>${manualMode?'Map entered clip time':'Map current video time'}</button><button class="btn" data-jump="${esc(m.id)}" ${isMapped?'':'disabled'}>Jump to moment</button></div>`;listNode.appendChild(el);}
listNode.querySelectorAll('[data-map]').forEach(b=>b.addEventListener('click',()=>mapMoment(b.dataset.map)));
listNode.querySelectorAll('[data-jump]').forEach(b=>b.addEventListener('click',()=>jumpToMoment(b.dataset.jump)));}
function showActive(m,seconds){activeMomentId=m.id;activeNode.innerHTML=`<div class="label">CURRENT HIGHLIGHT MOMENT · VIDEO ${secLabel(seconds)}</div><h2>${esc(m.title)}</h2><div class="key">${esc(m.team)} · ${esc(m.player)} · Match context: ${esc(m.match_time)}</div><p>${esc(m.explanation)}</p><div class="key">Video offset: ${secLabel(Number(mapping[m.id]))} · Source: FIFA official final report</div>`;renderMoments();}
function updateActive(){const now=currentSeconds();clockNode.textContent=Number.isFinite(now)?'Video time: '+secLabel(now):'Video time: —';if(!Number.isFinite(now))return;const sorted=MOMENTS.filter(m=>Number.isFinite(Number(mapping[m.id]))&&Number(mapping[m.id])>=0).slice().sort((a,b)=>Number(mapping[a.id])-Number(mapping[b.id]));let found=null;for(const m of sorted){if(Number(mapping[m.id])<=now+0.15)found=m;else break;}if(found&&found.id!==activeMomentId)showActive(found,now);else if(!found&&activeMomentId!==null){activeMomentId=null;activeNode.innerHTML='<div class="label">BEFORE THE FIRST MAPPED MOMENT</div><h2>Keep watching</h2><p>PitchIQ has not reached a mapped highlight yet.</p>';renderMoments();}}
function mapMoment(id){const now=currentSeconds();if(!Number.isFinite(now)){statusNode.textContent=manualMode?'Enter a valid timestamp in the manual fallback box first.':'The video clock is unavailable. Start or pause the video, then try mapping again.';return;}mapping[id]=Math.round(now*10)/10;safeSave();statusNode.textContent='Mapped '+MOMENTS.find(m=>m.id===id).title+' to video '+secLabel(now)+'.';activeMomentId=null;renderMoments();updateActive();}
function jumpToMoment(id){const value=Number(mapping[id]);if(!Number.isFinite(value)){statusNode.textContent='Map this moment first by entering its clip timestamp.';return;}if(manualMode){manualTimeNode.value=secLabel(value);updateActive();statusNode.textContent='Previewing '+MOMENTS.find(m=>m.id===id).title+' at clip time '+secLabel(value)+'. Switch to YouTube and seek there manually; PitchIQ cannot control that separate player.';return;}try{player.seekTo(value,true);statusNode.textContent='Jumped to '+MOMENTS.find(m=>m.id===id).title+' at '+secLabel(value)+'.';}catch(e){statusNode.textContent='Could not seek to this moment.';}}
function startPlayer(){if(!window.YT||!window.YT.Player)return;player=new YT.Player('ytMount',{width:'100%',height:'100%',videoId:VIDEO_ID,playerVars:{playsinline:1,rel:0,modestbranding:1},events:{onReady:()=>{if(manualMode)return;playerReady=true;statusNode.textContent='Official FIFA video loaded. Play the clip and map each moment as it appears.';renderMoments();},onError:(e)=>{enableManualFallback(e.data);}}});}
safeLoad();renderMoments();
window.onYouTubeIframeAPIReady=startPlayer;
const script=document.createElement('script');script.src='https://www.youtube.com/iframe_api';script.onerror=()=>enableManualFallback(null,'Could not load the YouTube IFrame API.');document.head.appendChild(script);
document.getElementById('previewExternalTime').addEventListener('click',previewManualTime);
manualTimeNode.addEventListener('keydown',e=>{if(e.key==='Enter')previewManualTime();});
document.getElementById('resetMappings').addEventListener('click',()=>{mapping={};safeSave();activeMomentId=null;activeNode.innerHTML='<div class="label">WAITING FOR A MAPPED MOMENT</div><h2>Play the highlights</h2><p>Map the moments below as they appear in the video.</p>';renderMoments();statusNode.textContent='All manual video offsets were reset.';});
document.getElementById('openYoutube').addEventListener('click',()=>window.open('https://www.youtube.com/watch?v='+VIDEO_ID,'_blank','noopener'));
setInterval(updateActive,350);
</script>
</body></html>'''
    return (
        html.replace("__VIDEO_ID__", video_id_json)
        .replace("__MOMENTS__", moments_json)
        .replace("__REPORT_URL__", FIFA_REPORT_URL)
    )


def render_world_cup_final_demo() -> None:
    """Render the World Cup highlight page with a user-selectable YouTube source."""
    import streamlit as st
    import streamlit.components.v1 as components

    st.title("PitchIQ — YouTube Match Playback")
    st.caption(
        "Paste a YouTube video link to try it in the embedded player. Playback is "
        "controlled by YouTube's own embed permissions and availability rules."
    )

    url_key = "pitchiq_world_cup_demo_video_url"
    id_key = "pitchiq_world_cup_demo_video_id"
    current_url = st.session_state.get(url_key, FINAL_VIDEO_URL)
    with st.form("pitchiq_youtube_video_form", clear_on_submit=False):
        entered_url = st.text_input(
            "YouTube video link",
            value=current_url,
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
            help=(
                "Supports youtube.com/watch, youtu.be, youtube.com/shorts, "
                "youtube.com/live, and YouTube embed URLs."
            ),
        )
        submitted = st.form_submit_button("Load YouTube video")

    if submitted:
        selected_id = parse_youtube_video_id(entered_url)
        if not selected_id:
            st.error(
                "That link is not a recognized YouTube video URL. Paste a full "
                "youtube.com/watch, youtu.be, Shorts, Live, or embed link."
            )
        else:
            st.session_state[url_key] = entered_url.strip()
            st.session_state[id_key] = selected_id
            if selected_id == FINAL_VIDEO_ID:
                st.success("Official World Cup Final video selected.")
            else:
                st.success("YouTube video link accepted. Loading the selected video below.")

    selected_id = st.session_state.get(id_key, FINAL_VIDEO_ID)
    selected_url = st.session_state.get(
        url_key, f"https://www.youtube.com/watch?v={selected_id}"
    )
    st.markdown(f"Selected video: [Open on YouTube]({selected_url})")

    if selected_id != FINAL_VIDEO_ID:
        st.warning(
            "The video source has changed, but the three curated explanations below "
            "still describe the Spain–Argentina 2026 World Cup Final. They will not "
            "automatically become facts about the newly selected video. For another "
            "match, use Real Match Explorer with that match's own event data."
        )

    st.info(
        "PitchIQ uses YouTube's official IFrame Player API. If the video owner disables "
        "embedding, YouTube returns error 101/150, or the video is private/restricted, "
        "PitchIQ cannot override that restriction. The page will show a manual timestamp "
        "fallback and an Open on YouTube link. If embedded playback works, you can map "
        "the current video time to a curated moment. Mappings are stored separately per "
        "video in this browser when storage is available."
    )
    components.html(build_world_cup_final_html(selected_id), height=1180, scrolling=True)
    st.caption(
        "The curated Spain–Argentina moment facts are sourced from FIFA's final report. "
        "A custom YouTube URL changes playback only; it does not fetch a transcript, "
        "extract match events, or automatically generate new verified explanations. "
        "StatsBomb provides selected historical event data, not video access for every match."
    )
