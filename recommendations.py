"""Rule-based AI road safety recommendations driven by predicted severity and the input conditions."""

BASE = {
    "Fatal": [
        "HIGH RISK: enforce strict speed limits with speed cameras or calming measures on this stretch.",
        "Install crash barriers, rumble strips and retro-reflective signage; schedule increased highway patrolling.",
        "Prioritise a road-safety audit and make sure ambulance and trauma-centre response is ready along the corridor.",
    ],
    "Serious": [
        "Install warning signs and rumble strips and refresh lane markings and road studs.",
        "Increase enforcement of speed, helmet and seat-belt rules during high-risk hours.",
        "Review sight distances, shoulders and access points for quick low-cost fixes.",
    ],
    "Minor": [
        "Maintain regular road upkeep (potholes, markings, signage) to keep the risk low.",
        "Continue driver-awareness campaigns and keep monitoring accident trends for this stretch.",
    ],
}

EXTRA = {
    ("weather", "Heavy rain"): "Heavy rain: improve drainage, use anti-skid surfacing and display 'slippery road' warnings.",
    ("weather", "Light rain"): "Rain: check drainage and surface grip, and show advisory speed limits.",
    ("weather", "Mist/Fog"): "Fog: add fog lights, reflective road studs and variable message boards with advisory speeds.",
    ("weather", "Dust storm"): "Dust storm: issue weather alerts and install visibility-warning signs.",
    ("weather", "Strong wind"): "Strong wind: add wind-warning signs and restrict high-sided vehicles during alerts.",
    ("time_of_day", "Night"): "Night: improve lighting at junctions and villages, add reflectors and run checks against drunk driving.",
    ("vehicle_type", "Truck"): "Trucks: enforce speed and load compliance, and provide truck lay-bys to reduce fatigue.",
    ("vehicle_type", "MAV"): "Multi-axle vehicles: enforce lane discipline and speed limits, and add rest areas.",
    ("vehicle_type", "LCV"): "Light commercial vehicles: check speed governors and overloading.",
    ("vehicle_type", "Bus"): "Buses: strengthen driver fatigue management and speed-governor checks.",
    ("vehicle_type", "Two-wheeler"): "Two-wheelers: enforce helmet use and provide paved shoulders or separated lanes.",
    ("vehicle_type", "Three-wheeler"): "Three-wheelers: restrict them on high-speed lanes and provide service roads.",
    ("vehicle_type", "Pedestrian"): "Pedestrians: add foot-over-bridges, underpasses, zebra crossings and footpaths.",
    ("vehicle_type", "Cycle"): "Cyclists: provide shoulders or cycle tracks and reflective markers.",
    ("vehicle_type", "Tractor"): "Tractors: provide reflectors and restrict slow vehicles from fast lanes.",
    ("vehicle_type", "Animal"): "Animals: install fencing and animal-crossing warning signs.",
    ("road_condition", "Sharp curve"): "Sharp curve: add chevron signs, advance warnings and reduce the approach speed limit.",
    ("road_condition", "Slight curve"): "Curve: add chevron signs and clear lane markings on the approach.",
    ("road_condition", "Steep incline"): "Steep incline: add warning signs, runaway-vehicle provisions and speed limits.",
    ("road_condition", "Dip"): "Dip: add warning signs and fix drainage to avoid water logging.",
    ("road_condition", "Hump"): "Hump: improve visibility and add advance warning signs.",
    ("road_type", "Single lane"): "Single lane: widen the carriageway or add passing zones and shoulder improvements.",
    ("road_type", "Two lanes"): "Two-lane road: add median markings and overtaking restrictions where visibility is poor.",
    ("road_type", "Three+ lanes (undivided)"): "Undivided multi-lane road: install a median barrier to prevent head-on crashes.",
    ("road_type", "Four+ lanes (divided)"): "Divided highway: enforce lane discipline and keep median barriers and signage in good repair.",
    ("area_type", "Urban"): "Urban section: control access points, add service roads and pedestrian crossings.",
    ("area_type", "Rural"): "Rural section: add warning signs near villages, speed breakers at settlements and street lighting.",
    ("cause", "Overspeeding"): "Overspeeding: use speed cameras, average-speed enforcement and speed-limit signage.",
    ("cause", "Drunken driving"): "Drunken driving: run breath-analyser checks at night and on weekends.",
    ("cause", "Vehicle out of control"): "Loss of control: improve surface friction, markings and roadside crash protection.",
}


def build_recommendations(severity, conditions):
    """Return a list of recommendation strings for a predicted severity and condition dict."""
    items = list(BASE.get(severity, BASE["Minor"]))
    for field, value in conditions.items():
        text = EXTRA.get((field, value))
        if text:
            items.append(text)
    return items
