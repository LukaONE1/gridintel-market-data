
"""GRIDINTEL v0.9 — experimental NFL moneyline model.

Requires pregame team-strength ratings from an external,
validated data process. Not a live prediction service.
"""

from math import pow


def win_probability(
    home_rating: float,
    away_rating: float,
    home_advantage: float = 45.0,
    scale: float = 400.0,
) -> dict:
    """Estimate win probabilities using an Elo-style formula.

    Ratings must be calculated using information available
    before the game. Default parameters are uncalibrated.
    """
    if scale <= 0:
        raise ValueError("scale must be positive")

    difference = home_rating + home_advantage - away_rating
    home_probability = 1 / (1 + pow(10, -difference / scale))

    return {
        "home_win_probability": round(home_probability, 4),
        "away_win_probability": round(1 - home_probability, 4),
        "model": "experimental_elo_baseline",
        "validated": False,
    }


if __name__ == "__main__":
    example = win_probability(
        home_rating=1500,
        away_rating=1500,
    )
    print("Illustrative test only:", example)
