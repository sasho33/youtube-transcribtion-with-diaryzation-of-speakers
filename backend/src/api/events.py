# backend/src/api/events.py
from flask_restx import Namespace, Resource, fields
from flask import request
from ..services.events_service import list_events, get_event_by_title

ns = Namespace("events", description="Event listings (EvW & KOTT)")

# Keep models simple; your event JSON can vary. Use Raw to passthrough.
event_model = ns.model("Event", {"event_title": fields.String})
list_model = ns.model("EventList", {
    "count": fields.Integer,
    "results": fields.List(fields.Raw)
})

@ns.route("/")
class EventsCombined(Resource):
    @ns.doc(params={
        "source": "Filter by source: evw | kott",
        "title": "Exact event title to fetch a single event"
    })
    def get(self):
        source = request.args.get("source")
        title = request.args.get("title")
        if title and source in ("evw", "kott"):
            event = get_event_by_title(source, title)
            if not event:
                ns.abort(404, f"Event '{title}' not found in {source}.")
            return event, 200
        # otherwise list
        data = list_events(source)
        return {"count": len(data), "results": data}, 200

@ns.route("/evw")
class EventsEvW(Resource):
    @ns.marshal_with(list_model)
    def get(self):
        data = list_events("evw")
        return {"count": len(data), "results": data}, 200

@ns.route("/kott")
class EventsKOTT(Resource):
    @ns.marshal_with(list_model)
    def get(self):
        data = list_events("kott")
        return {"count": len(data), "results": data}, 200

@ns.route("/<string:source>/<path:event_title>")
@ns.param("source", "evw | kott")
@ns.param("event_title", "URL-encoded title, e.g. East%20vs%20West%2018")
class EventDetail(Resource):
    def get(self, source, event_title):
        if source not in ("evw", "kott"):
            ns.abort(400, "source must be 'evw' or 'kott'")
        event = get_event_by_title(source, event_title)
        if not event:
            ns.abort(404, f"Event '{event_title}' not found in {source}.")
        return event, 200

@ns.route("/by-title/<path:event_title>")
@ns.param("event_title", "URL-encoded event title, e.g. East%20vs%20West%2018")
class EventDetailByTitle(Resource):
    def get(self, event_title):
        event = get_event_by_title_any(event_title)
        if not event:
            ns.abort(404, f"Event '{event_title}' not found in EvW or KOTT.")
        return event, 200
