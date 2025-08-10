# backend/src/api/athletes.py
from flask_restx import Namespace, Resource, fields
from flask import request
from src.services.athlete_service import get_all_athletes, get_athlete_by_name



ns = Namespace("athletes", description="Athlete data")

# minimal model to prove it shows up in Swagger; expand later
athlete_model = ns.model("Athlete", {
    "name": fields.String,
    "country": fields.String,
})

list_response_model = ns.model("AthleteListResponse", {
    "count": fields.Integer,
    "results": fields.List(fields.Raw),
})

@ns.route("/")  # <= IMPORTANT: use "/" here
class AthleteList(Resource):
    @ns.marshal_with(list_response_model)
    @ns.doc(params={"q": "Search by name", "country": "Exact country match"})
    def get(self):
        q = request.args.get("q")
        country = request.args.get("country")
        data = get_all_athletes(q=q, country=country)
        return {"count": len(data), "results": data}

@ns.route("/<string:name>")  # becomes /athletes/<name>
class AthleteDetail(Resource):
    # @ns.marshal_with(athlete_model)
    def get(self, name):
        obj = get_athlete_by_name(name)
        if not obj:
            ns.abort(404, f"Athlete '{name}' not found")
        return obj
