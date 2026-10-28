"""Additive local web UI for PitchIQ's existing analysis agents.

This module leaves the existing Streamlit dashboard untouched. It serves a
self-contained browser UI and calls PitchIQ's current analysis pipeline.
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pitchiq.agents import PitchIQOrchestrator
from pitchiq.importers import CSV_TEMPLATE, parse_uploaded_match
from pitchiq.main import analyze_match, load_match

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "webui"
HOST = os.getenv("PITCHIQ_UI_HOST", "127.0.0.1")
PORT = int(os.getenv("PITCHIQ_UI_PORT", "8765"))
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


def make_payload(match: dict, audience: str = "fan") -> dict:
    """Run the existing three-agent workflow and return JSON-safe UI state."""
    if audience not in {"fan", "analyst"}:
        raise ValueError("Audience must be 'fan' or 'analyst'.")
    if not isinstance(match, dict) or not isinstance(match.get("events"), list):
        raise ValueError("A match object with an events list is required.")

    result = PitchIQOrchestrator(analyze_match).run(match, audience)
    state = result["shared_state"]
    return {
        "match": match,
        "report": state["report"],
        "insights": state["insights"],
        "verification": state["verification"],
        "steps": result["steps"],
        "handoffs": result["handoffs"],
        "audience": audience,
        "ai_enabled": os.getenv("PITCHIQ_USE_LOCAL_AI", "0").strip().lower() in {"1", "true", "yes", "on"},
    }


def answer_match_question(match: dict, question: str) -> dict:
    """Answer a narrow match question from recorded events only.

    This is an evidence-grounded query helper, not a predictive model. It
    deliberately declines questions that require metrics the current engine
    does not calculate (xG, possession, calibrated probabilities, or pressing
    intensity). Evidence IDs returned here come directly from the event log.
    """
    if not isinstance(match, dict) or not isinstance(match.get("events"), list):
        raise ValueError("A match object with an events list is required.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Enter a question about this match first.")
    question = question.strip()
    if len(question) > 500:
        raise ValueError("Keep the question under 500 characters.")

    q = re.sub(r"[^a-z0-9%+.' -]", " ", question.lower())
    q = re.sub(r"\s+", " ", q).strip()
    events = sorted(
        match["events"],
        key=lambda event: (event.get("minute", 0), event.get("id", 0)),
    )
    report = analyze_match(match)
    home, away = report["home_team"], report["away_team"]
    score = report["score"]
    stats = report["stats"]
    by_id = {event.get("id"): event for event in events}

    def response(answer: str, ids=(), source="recorded match events") -> dict:
        return {
            "answer": answer,
            "evidence_event_ids": list(dict.fromkeys(ids)),
            "source": source,
            "mode": "evidence-grounded",
        }

    unavailable_terms = (
        "xg", "expected goal", "goal probability", "probability", "possession",
        "pressing intensity", "press intensity", "expected threat", " xt ",
        "field tilt", "line break", "line-breaking", "player rating",
        "pass network",
    )
    padded = f" {q} "
    if any(term in padded for term in unavailable_terms):
        return response(
            "That metric is not calculated by the current PitchIQ engine. "
            "I won't estimate it from event counts. I can report recorded shots, "
            "passes and outcomes, tackles won, goal events, and detected attacking "
            "sequences. The chart on this screen shows recorded shot activity, "
            "not a prediction.",
            source="model capability boundary",
        )

    if any(word in q for word in ("score", "result", "who is ahead", "scoreline")):
        ids = [e.get("id") for e in events if e.get("type") == "goal" or e.get("outcome") in {"goal", "scored"}]
        return response(
            f"The recorded score is {home} {score[home]}–{score[away]} {away}. "
            f"This is calculated from the goal events in the supplied match data.",
            ids,
        )

    if "shot" in q or "shots on target" in q:
        details=[]
        ids=[]
        for team in (home, away):
            team_shots=[e for e in events if e.get("team")==team and e.get("type") in {"shot", "goal"}]
            targeted=[e for e in team_shots if e.get("type")=="goal" or e.get("outcome") in {"on_target", "saved", "goal", "scored"}]
            details.append(f"{team}: {len(team_shots)} recorded shot/goal event(s), {len(targeted)} marked on target by recorded outcome")
            ids.extend(e.get("id") for e in team_shots)
        return response("; ".join(details)+". On-target classification follows the source outcomes, not a separate tracking model.", ids)

    if "pass" in q or "passing" in q:
        details=[]; ids=[]
        for team in (home, away):
            stat=stats[team]
            accuracy=stat.get("pass_accuracy_pct")
            accuracy_text=f"{accuracy}%" if accuracy is not None else "not available (no recorded pass attempts)"
            details.append(f"{team}: {stat.get('passes_completed',0)}/{stat.get('passes_attempted',0)} passes completed; accuracy {accuracy_text}")
            ids.extend(e.get("id") for e in events if e.get("team")==team and e.get("type")=="pass")
        return response("Recorded passing: "+"; ".join(details)+".", ids)

    if "tackle" in q:
        details=[]; ids=[]
        for team in (home, away):
            stat=stats[team]
            details.append(f"{team}: {stat.get('tackles_won',0)} recorded tackles won")
            ids.extend(e.get("id") for e in events if e.get("team")==team and e.get("type")=="tackle")
        return response("; ".join(details)+".", ids)

    if any(word in q for word in ("goal", "scored", "breakthrough")):
        goal_events=[e for e in events if e.get("type")=="goal" or e.get("outcome") in {"goal", "scored"}]
        if not goal_events:
            return response("There are no goal events in the current event log. I can't infer a goal from shots or commentary alone.")
        clauses=[]; ids=[]
        sequences=report.get("attacking_sequences", [])
        for goal in goal_events[:5]:
            goal_id=goal.get("id"); ids.append(goal_id)
            matching=next((seq for seq in sequences if seq.get("event_ids") and seq["event_ids"][-1]==goal_id), None)
            basic=f"At minute {goal.get('minute')}, {goal.get('team')} recorded a goal event (event ID {goal_id})"
            if matching:
                seq_ids=matching.get("event_ids",[]); ids.extend(seq_ids)
                basic+=f" after a detected sequence of {matching.get('passes')} completed pass(es) from minute {matching.get('start_minute')} to {matching.get('end_minute')} (evidence IDs {', '.join(map(str,seq_ids))})"
            else:
                basic+="; no attacking sequence met the current evidence rules for this goal, so its build-up cannot be attributed from this data"
            clauses.append(basic)
        return response(". ".join(clauses)+". These are recorded events, not proof of tactical causation.", ids)

    if any(word in q for word in ("story", "sequence", "why", "outcome", "moment", "attack", "matters")):
        sequences=report.get("attacking_sequences",[])
        if not sequences:
            return response("No attacking sequence matched PitchIQ's current rules in this dataset. I can still show recorded shots, passes, tackles, and goal events, but I won't invent a build-up narrative.")
        clauses=[]; ids=[]
        for seq in sequences[:3]:
            ids.extend(seq.get("event_ids",[]))
            finish="goal" if seq.get("finish")=="goal" else "shot"
            clauses.append(f"{seq.get('team')} completed {seq.get('passes')} pass(es) from minute {seq.get('start_minute')} to {seq.get('end_minute')}, followed by a recorded {finish}; supporting event IDs: {', '.join(map(str,seq.get('event_ids',[])))}")
        return response("Evidence-linked sequence(s): "+". ".join(clauses)+". This describes event order; it does not by itself prove the sequence caused a goal or created a high-quality chance.", ids)

    if "player" in q or "who " in q:
        players={}
        for event in events:
            name=event.get("player")
            if not name or name=="Not supplied":
                continue
            key=(event.get("team"),name)
            item=players.setdefault(key,{"count":0,"goals":0,"ids":[]})
            item["count"]+=1; item["ids"].append(event.get("id"))
            if event.get("type")=="goal" or event.get("outcome") in {"goal","scored"}:
                item["goals"]+=1
        ranked=sorted(players.items(),key=lambda item:(-item[1]["count"],-item[1]["goals"],item[0][1]))
        if not ranked:
            return response("The event file does not include player names, so I can't produce a player-level summary.")
        (team,name),item=ranked[0]
        return response(f"{name} ({team}) has the highest recorded event involvement in this file with {item['count']} event(s) and {item['goals']} goal event(s). This is event involvement, not an official player rating or Player of the Match judgment.",item["ids"])

    if "event" in q or "data" in q or "match" in q:
        return response(f"This match contains {len(events)} recorded events. PitchIQ can summarize the score ({home} {score[home]}–{score[away]} {away}), shots, passing, tackles, goal events, and evidence-linked sequences. It doesn't currently calculate validated xG, possession, or goal probabilities.")

    return response("I can answer from this match's event log. Try asking about the score, shots, passing accuracy, tackles won, recorded goals, a supported attacking sequence, or player event involvement. For metrics such as xG, possession, pressing intensity, and goal probability, the current engine reports them as unavailable rather than guessing.")


class PitchIQHandler(BaseHTTPRequestHandler):
    server_version = "PitchIQLocalUI/1.0"

    def log_message(self, fmt: str, *args) -> None:
        # Keep the terminal useful without logging uploaded event contents.
        print(f"[PitchIQ UI] {self.address_string()} - {fmt % args}")

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' data:; img-src 'self' data:; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        self.end_headers()

    def _send_bytes(self, status: int, payload: bytes, content_type: str) -> None:
        self._headers(status, content_type, len(payload))
        self.wfile.write(payload)

    def _send_json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, raw, "application/json; charset=utf-8")

    def _read_body(self) -> bytes:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid Content-Length header.") from None
        if size < 0 or size > MAX_UPLOAD_BYTES:
            raise ValueError("Request body is too large. The limit is 15 MB.")
        return self.rfile.read(size)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            index = WEB_ROOT / "index.html"
            if not index.is_file():
                self._send_json(500, {"error": "The PitchIQ web UI file is missing."})
                return
            self._send_bytes(200, index.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/health":
            self._send_json(200, {"ok": True, "service": "PitchIQ local UI", "host": HOST, "port": PORT})
        elif path == "/api/demo":
            try:
                self._send_json(200, make_payload(load_match()))
            except Exception as exc:  # surfaced as a clear local app error
                self._send_json(500, {"error": f"Could not load the bundled demo: {exc}"})
        elif path == "/api/template.csv":
            self._send_bytes(200, CSV_TEMPLATE.encode("utf-8"), "text/csv; charset=utf-8")
        else:
            self._send_json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/assistant":
            try:
                body = self._read_body()
                request = json.loads(body.decode("utf-8"))
                result = answer_match_question(request.get("match"), request.get("question", ""))
                self._send_json(200, result)
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "Expected a UTF-8 JSON request."})
            except (TypeError, ValueError, KeyError) as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": f"PitchIQ assistant failed: {exc}"})
            return

        if parsed.path == "/api/analyze":
            try:
                body = self._read_body()
                request = json.loads(body.decode("utf-8"))
                payload = make_payload(request.get("match"), request.get("audience", "fan"))
                self._send_json(200, payload)
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "Expected a UTF-8 JSON request."})
            except (TypeError, ValueError, KeyError) as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": f"PitchIQ analysis failed: {exc}"})
            return

        if parsed.path == "/api/upload":
            try:
                query = parse_qs(parsed.query)
                filename = Path(query.get("filename", [""])[0]).name
                if not filename.lower().endswith((".csv", ".json")):
                    raise ValueError("Choose a .csv or .json event log.")
                body = self._read_body()
                match = parse_uploaded_match(filename, body)
                audience = query.get("audience", ["fan"])[0]
                self._send_json(200, make_payload(match, audience))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "Could not read this file as UTF-8 CSV/JSON."})
            except (TypeError, ValueError, KeyError) as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": f"PitchIQ could not process the upload: {exc}"})
            return

        self._send_json(404, {"error": "Not found."})


def main() -> None:
    """Start the additive browser interface on loopback by default."""
    if not (WEB_ROOT / "index.html").is_file():
        raise SystemExit(f"Missing web UI at {WEB_ROOT / 'index.html'}")
    server = ThreadingHTTPServer((HOST, PORT), PitchIQHandler)
    print("\nPitchIQ Figma-reference UI")
    print(f"Local URL: http://{HOST}:{PORT}")
    print("Using the existing PitchIQ agents and match-analysis engine.")
    print("Press Ctrl+C to stop this UI. The Streamlit dashboard is unaffected.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PitchIQ web UI...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
