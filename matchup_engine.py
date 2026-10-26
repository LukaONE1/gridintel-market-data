
"""GRIDINTEL Matchup Intelligence Engine v0.1.

Analyzes pregame NFL team statistics to identify matchup
advantages. Experimental only; no validated predictions.
"""

from typing import Dict


def analyze_matchup(
    home_team: str,
    away_team: str,
    home_stats: Dict[str, float],
    away_stats: Dict[str, float],
) -> dict:
    """Compare two teams using pregame performance statistics."""

    metrics = {
        "offensive_epa": {
            "label": "Offensive EPA per play",
            "higher_is_better": True,
        },
        "defensive_epa_allowed": {
            "label": "Defensive EPA allowed per play",
            "higher_is_better": False,
        },
        "success_rate": {
            "label": "Offensive success rate",
            "higher_is_better": True,
        },
        "explosive_play_rate": {
            "label": "Explosive play rate",
            "higher_is_better": True,
        },
    }

    comparisons = []

    for metric, config in metrics.items():
        home_value = home_stats.get(metric)
        away_value = away_stats.get(metric)

        if home_value is None or away_value is None:
            advantage = "insufficient_data"
        elif home_value == away_value:
            advantage = "even"
        else:
            home_better = (
                home_value > away_value
                if config["higher_is_better"]
                else home_value < away_value
            )
            advantage = home_team if home_better else away_team

        comparisons.append({
            "metric": metric,
            "label": config["label"],
            "home_value": home_value,
            "away_value": away_value,
            "advantage": advantage,
        })

    return {
        "home_team": home_team,
        "away_team": away_team,
        "comparisons": comparisons,
        "validated": False,
        "data_status": "external_pregame_data_required",
    }
