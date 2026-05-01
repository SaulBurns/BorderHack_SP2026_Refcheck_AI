BASKETBALL_RULES = {
    "block_charge": {
        "call_type": "Block / Charge",
        "rule_applied": "Legal guarding position and contact responsibility",
        "summary": (
            "A defender must establish legal guarding position before contact. "
            "If the defender is still moving into the ball handler's path at impact, "
            "the contact is usually a blocking foul."
        ),
    },
    "shooting_contact": {
        "call_type": "Shooting Foul",
        "rule_applied": "Illegal contact affecting a try for goal",
        "summary": (
            "A defender may contest vertically, but contact on the shooter's arm, body, "
            "or landing space that affects the shot can be a defensive foul."
        ),
    },
    "out_of_bounds": {
        "call_type": "Out of Bounds",
        "rule_applied": "Last touch before the ball becomes out of bounds",
        "summary": (
            "Possession is awarded against the player who last touched the ball before "
            "it contacted a boundary line, the floor outside the court, or an object out of play."
        ),
    },
    "travel": {
        "call_type": "Traveling",
        "rule_applied": "Illegal movement of the pivot foot or steps without a dribble",
        "summary": (
            "A player who has gathered the ball must release a shot or pass, or begin a "
            "legal dribble, before taking too many steps or illegally moving the pivot foot."
        ),
    },
    "goaltending": {
        "call_type": "Goaltending / Basket Interference",
        "rule_applied": "Illegal contact with a shot on its downward flight or around the cylinder",
        "summary": (
            "A defender may not touch a try that is on its downward flight with a chance "
            "to score, or interfere with the ball while it is on or within the basket cylinder."
        ),
    },
}


DEFAULT_BASKETBALL_RULE = BASKETBALL_RULES["block_charge"]
