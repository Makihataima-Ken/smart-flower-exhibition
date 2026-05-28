# engine/knowledge_engine.py

from experta import *

from models.facts import (
    Grid,
    Warehouse,
    Robot,
    Pavilion,
    State
)


class FlowerShopEngine(KnowledgeEngine):

    @DefFacts()
    def initial_facts(self):

        yield Grid(
            width=6,
            height=6
        )

        yield Warehouse(
            x=2,
            y=3
        )

        yield Robot(
            x=3,
            y=1,
            inventory=[],
            load=0,
            max_load=4
        )

        yield Pavilion(
            pavilion_id=1,
            flower_type="Rose",
            x=2,
            y=4,
            needs={
                "Red": 2,
                "Pink": 1,
                "White": 1
            }
        )

        yield Pavilion(
            pavilion_id=2,
            flower_type="Tulip",
            x=4,
            y=3,
            needs={
                "Red": 3,
                "Yellow": 1
            }
        )