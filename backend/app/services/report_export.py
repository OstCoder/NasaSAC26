"""Phase 5 Task 3: the mission report as a standalone Markdown document.

The JSON envelope (:mod:`mission_report`) is for machines; a reviewer, a judge or
a teammate wants one file they can read. This module renders the same numbers as
tables and prose, with the assumptions, provenance and limitations attached.

It adds no calculation: every value comes from ``mission_report`` and
``engineering_response``. There is no wall clock and no random ordering, so the
same committed inputs produce the same bytes (a test asserts that).
"""

from __future__ import annotations

from app.core.settings import Settings, get_settings
from app.services.engineering import engineering_response
from app.services.mission_report import mission_report

SCHEMA = "lunanav.mission_report_markdown.v1"


def _f(value, digits: int = 2, dash: str = "—") -> str:
    if value is None:
        return dash
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def mission_report_markdown(*, site_id: str, window: str = "initial",
                            settings: Settings | None = None) -> str:
    """One deterministic Markdown mission report for a site and window."""
    settings = settings or get_settings()
    report = mission_report(site_id=site_id, window=window, settings=settings)
    engineering = engineering_response(site_id=site_id, window=window, settings=settings)

    site = report["site"]
    run = report["window"]
    terrain = report["terrain"]
    power = engineering["power"]
    link = engineering["link"]
    requirement_rows = [
        [
            check["label"],
            _f(check["value"], 1) + (" " + check["unit"] if check["unit"] == "h" else " %"),
            ("at least " if check["comparison"] == "at_least" else "at most ")
            + _f(check["threshold"], 1),
            check["status"].upper(),
            "window-limited" if check["censored"] else "measured",
        ]
        for check in report["requirements"]["checks"]
    ]
    design_rows = [
        [design["label"], _f(design["peak_w"], 0) + " W", _f(design["energy_wh"], 0) + " Wh",
         _f(design["capacity_factor_pct"], 1) + " %"]
        for design in power["designs"]
    ]
    battery = power["budget"]["battery"]

    def link_row(label: str, case: dict | None) -> list[str]:
        if not case:
            return [label, "—", "—", "—", "—"]
        return [
            label,
            _f(case["range_km"], 0) + " km",
            _f(case["cn0_db_hz"], 1) + " dB-Hz",
            _f(case["supported_rate_bps"] / 1e6, 2) + " Mbps",
            _f(case["margin_db"], 1) + " dB",
        ]

    parts: list[str] = [
        f"# LunaNav mission report — {site['name']} ({site['site_id']})",
        "",
        f"Mission window: **{run['label']}** (`{run['key']}`), {run['start_utc']} to "
        f"{run['stop_utc']}, {run['samples']} stored samples at {run['step']}. "
        f"Site coordinates {_f(site['latitude_deg'], 4)}°, {_f(site['longitude_deg'], 4)}° "
        f"(planetocentric east-positive), surface elevation {_f(site['elevation_m'], 1)} m.",
        "",
        "## Terrain basis",
        "",
        f"- Skyline basis: **{terrain['basis']}**"
        + (" (flat geometric horizon; no committed LOLA mask covers this point)"
           if terrain["geometric_only"] else ", from the committed two-tier LOLA mask"),
        f"- Observer height {_f(terrain['observer_height_m'], 1)} m; near pixels "
        f"{_f((terrain['coverage'] or {}).get('near', {}).get('pixel_m'), 0)} m, far pixels "
        f"{_f((terrain['coverage'] or {}).get('far', {}).get('pixel_m'), 0)} m to "
        f"{_f((terrain['coverage'] or {}).get('max_sampled_range_km'), 0)} km",
        f"- Maximum obstruction {_f(terrain['max_obstruction_deg'], 2)}° at azimuth "
        f"{_f(terrain['max_obstruction_azimuth_deg'], 1)}°",
        "",
        "## Visibility against the terrain",
        "",
        _table(
            ["Body", "Availability", "Visible time", "Longest outage", "Terrain-blocked samples"],
            [
                ["Sun", _f(report["sunlight"]["availability_percent"], 1) + " %",
                 _f(report["sunlight"]["visible_hours"], 1) + " h",
                 _f(report["sunlight"]["longest_darkness_hours"], 1) + " h",
                 _f(terrain["sun_blocked_by_terrain"])],
                ["Earth", _f(report["earth"]["visibility_percent"], 1) + " %",
                 _f(report["earth"]["visible_hours"], 1) + " h",
                 _f(report["earth"]["longest_blackout_hours"], 1) + " h",
                 _f(terrain["earth_blocked_by_terrain"])],
                ["Sun and Earth", _f(report["simultaneous_visibility"]["availability_percent"], 1) + " %",
                 _f(report["simultaneous_visibility"]["visible_hours"], 1) + " h",
                 _f(report["simultaneous_visibility"]["longest_gap_hours"], 1) + " h",
                 "—"],
            ],
        ),
        "",
        "## Phase 1 requirements",
        "",
        _table(["Requirement", "Measured", "Target", "Status", "Measurement"], requirement_rows),
        "",
        f"Requirement source: {report['requirements']['source']}. "
        f"Overall: **{_f(report['requirements']['satisfied'])}**. "
        "`UNKNOWN` is not a pass: the window-limited value cannot decide it.",
        "",
        "## Power budget",
        "",
        f"Array energy is shown for both geometries; the battery is stepped with the "
        f"**{power['design']['recommended']}** design. {power['design']['reason']}",
        "",
        _table(["Array", "Peak", "Energy", "Capacity factor"], design_rows),
        "",
        f"- Window: {_f(power['window']['hours'], 1)} h, sunlit "
        f"{_f(power['window']['sunlit_hours'], 1)} h ({_f(power['window']['sunlit_pct'], 1)} %)",
        f"- Load {_f(power['budget']['load_w'], 0)} W = {_f(power['budget']['load_wh'], 0)} Wh; "
        f"array {_f(power['budget']['array_energy_wh'], 0)} Wh; net "
        f"{_f(power['budget']['net_wh'], 0)} Wh",
        f"- Battery {_f(battery['capacity_wh'], 0)} Wh at {_f(battery['initial_soc_pct'], 0)} % "
        f"initial, minimum {_f(battery['min_soc_pct'], 1)} %, final "
        f"{_f(battery['final_soc_pct'], 1)} %; unserved {_f(battery['unserved_wh'], 0)} Wh",
        "",
        f"**{battery['verdict']}**",
        "",
        "## Direct-to-Earth link budget",
        "",
        _table(["Case", "Range", "C/N0", "Supported rate", "Margin"],
               [link_row("Best", link["best_case"]), link_row("Worst", link["worst_case"])]),
        "",
        f"- Earth line of sight: {_f(link['window']['visible_hours'], 1)} h of "
        f"{_f(link['window']['hours'], 1)} h; data volume "
        f"{_f(link['window']['data_volume_bound_mb'], 1)} MB bound; outage "
        f"{_f(link['window']['outage_hours'], 1)} h",
        f"- Assumed {_f(link['assumptions']['frequency_ghz'], 2)} GHz, "
        f"{_f(link['assumptions']['transmit_power_w'], 1)} W into "
        f"{_f(link['assumptions']['transmit_antenna_gain_dbi'], 0)} dBi, "
        f"{_f(link['assumptions']['receive_dish_diameter_m'], 0)} m dish, "
        f"{_f(link['assumptions']['required_ebno_db'], 1)} dB required Eb/N0",
        "",
        f"**{link['verdict']}**",
        "",
        "## Assumptions",
        "",
        f"- Power: {power['assumptions']['basis']}",
        f"- Link: {link['assumptions']['basis']}",
        "",
        "## Provenance",
        "",
        f"- Ephemeris: {report['model']['ephemeris']}",
        f"- Terrain: {report['model']['terrain']} ({report['model']['terrain_provenance']})",
        f"- Sampling: {report['model']['sampling']}",
        f"- Visibility rule: {report['model']['rule']['sun']} for the Sun, "
        f"{report['model']['rule']['earth']} for Earth",
        "",
        "## What this report does not claim",
        "",
        *[f"- {note}" for note in [*report["notes"], *power["limits"], *link["limits"]]],
        "",
        "---",
        "",
        "Regenerate with: "
        f"`curl 'http://localhost:8000/api/mission-report.md?site_id={site_id}&window={run['key']}'`. "
        "Same committed data in, same document out.",
        "",
    ]
    return "\n".join(parts)
