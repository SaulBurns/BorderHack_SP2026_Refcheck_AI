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
    "restricted_area": {
        "call_type": "Restricted Area",
        "rule_applied": "Secondary defender position inside the restricted area",
        "summary": (
            "A secondary defender generally cannot establish legal guarding position "
            "inside the restricted area against an offensive player who is in control "
            "of the ball or in the act of shooting. The defender's feet, timing, and "
            "whether they are primary or secondary are decisive."
        ),
    },
    "verticality": {
        "call_type": "Verticality",
        "rule_applied": "Legal vertical contest and cylinder principle",
        "summary": (
            "A defender may jump vertically within their own cylinder to contest a shot. "
            "Illegal contact is more likely when the defender moves forward, sideways, "
            "or into the shooter's body, arm, or landing space rather than maintaining verticality."
        ),
    },
    "airborne_shooter": {
        "call_type": "Airborne Shooter",
        "rule_applied": "Contact with an airborne player before returning to the floor",
        "summary": (
            "An airborne shooter is entitled to return safely to the floor. Contact "
            "that affects the shooter's body, arm, or landing space before they land "
            "can be a defensive foul unless the defender had already established a legal position."
        ),
    },
    "incidental_contact": {
        "call_type": "Incidental Contact",
        "rule_applied": "Contact that does not affect rhythm, speed, balance, or quickness",
        "summary": (
            "Not all contact is a foul. Contact may be incidental when it does not "
            "displace a player or affect rhythm, speed, balance, or quickness."
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
