"""Staff-facing Grazioso filter UI. Run as a normal Python process, not a notebook.

Credentials and role come from the environment. Default role is staff (read only).
If MONGO_USER / MONGO_PASS are unset, the dashboard uses an in-memory mongomock
database with a small seed set so it can be opened without a live cluster.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import dash
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px

from animal_shelter import AnimalShelter
from demo import build_shelter

RESCUE_FILTERS = {
    "Water Rescue": {
        "breed": {"$in": ["Labrador Retriever Mix", "Chesapeake Bay Retriever", "Newfoundland"]},
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "Mountain or Wilderness Rescue": {
        "breed": {
            "$in": [
                "German Shepherd",
                "Alaskan Malamute",
                "Old English Sheepdog",
                "Siberian Husky",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "Disaster or Individual Tracking": {
        "breed": {
            "$in": [
                "Doberman Pinscher",
                "German Shepherd",
                "Golden Retriever",
                "Bloodhound",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 20, "$lte": 300},
    },
}

COLUMNS = [
    "animal_id",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
    "outcome_type",
]


def create_app(shelter: Optional[AnimalShelter] = None):
    shelter = shelter if shelter is not None else build_shelter()
    app = dash.Dash(__name__)
    app.title = "Grazioso Salvare — candidate filter"
    app.layout = html.Div(
        [
            html.H2("Grazioso Salvare candidate filter"),
            html.P("Role: " + shelter.role + " (read-only unless DASH_ROLE=admin)"),
            dcc.Dropdown(
                id="rescue-type",
                options=[{"label": "All", "value": "All"}]
                + [{"label": k, "value": k} for k in RESCUE_FILTERS],
                value="All",
                clearable=False,
            ),
            dcc.Graph(id="breed-pie"),
            dash_table.DataTable(
                id="results",
                page_size=15,
                style_table={"overflowX": "auto"},
            ),
        ],
        style={"maxWidth": "1100px", "margin": "1rem auto", "fontFamily": "sans-serif"},
    )

    @app.callback(
        Output("results", "data"),
        Output("results", "columns"),
        Output("breed-pie", "figure"),
        Input("rescue-type", "value"),
    )
    def update(rescue_type):
        lookup = {} if rescue_type == "All" else RESCUE_FILTERS[rescue_type]
        rows = shelter.read(lookup)
        df = pd.DataFrame(rows)
        if df.empty:
            fig = px.pie(title="Breed distribution (no rows)")
            return [], [{"name": c, "id": c} for c in COLUMNS], fig
        keep = [c for c in COLUMNS if c in df.columns]
        counts = df["breed"].value_counts().reset_index() if "breed" in df.columns else pd.DataFrame()
        if counts.empty:
            fig = px.pie(title="Breed distribution")
        else:
            counts.columns = ["breed", "n"]
            fig = px.pie(counts.head(8), values="n", names="breed", title="Breed distribution")
        return df[keep].to_dict("records"), [{"name": c, "id": c} for c in keep], fig

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False, host="127.0.0.1", port=int(os.environ.get("DASH_PORT", "8050")))
