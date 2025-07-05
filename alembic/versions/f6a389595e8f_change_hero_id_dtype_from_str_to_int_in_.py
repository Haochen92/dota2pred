"""Change hero_id dtype from str to int in MatchTable

Revision ID: f6a389595e8f
Revises: 6a5fc8e63556
Create Date: 2025-07-03 11:55:16.079482

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6a389595e8f"
down_revision = "6a5fc8e63556"
branch_labels = None
depends_on = None

# --- Data Transformation Setup ---

raw_hero_data = {
    "1": "Anti-Mage",
    "2": "Axe",
    "3": "Bane",
    "4": "Bloodseeker",
    "5": "Crystal Maiden",
    "6": "Drow Ranger",
    "7": "Earthshaker",
    "8": "Juggernaut",
    "9": "Mirana",
    "10": "Morphling",
    "11": "Shadow Fiend",
    "12": "Phantom Lancer",
    "13": "Puck",
    "14": "Pudge",
    "15": "Razor",
    "16": "Sand King",
    "17": "Storm Spirit",
    "18": "Sven",
    "19": "Tiny",
    "20": "Vengeful Spirit",
    "21": "Windranger",
    "22": "Zeus",
    "23": "Kunkka",
    "25": "Lina",
    "26": "Lion",
    "27": "Shadow Shaman",
    "28": "Slardar",
    "29": "Tidehunter",
    "30": "Witch Doctor",
    "31": "Lich",
    "32": "Riki",
    "33": "Enigma",
    "34": "Tinker",
    "35": "Sniper",
    "36": "Necrophos",
    "37": "Warlock",
    "38": "Beastmaster",
    "39": "Queen of Pain",
    "40": "Venomancer",
    "41": "Faceless Void",
    "42": "Wraith King",
    "43": "Death Prophet",
    "44": "Phantom Assassin",
    "45": "Pugna",
    "46": "Templar Assassin",
    "47": "Viper",
    "48": "Luna",
    "49": "Dragon Knight",
    "50": "Dazzle",
    "51": "Clockwerk",
    "52": "Leshrac",
    "53": "Nature's Prophet",
    "54": "Lifestealer",
    "55": "Dark Seer",
    "56": "Clinkz",
    "57": "Omniknight",
    "58": "Enchantress",
    "59": "Huskar",
    "60": "Night Stalker",
    "61": "Broodmother",
    "62": "Bounty Hunter",
    "63": "Weaver",
    "64": "Jakiro",
    "65": "Batrider",
    "66": "Chen",
    "67": "Spectre",
    "68": "Ancient Apparition",
    "69": "Doom",
    "70": "Ursa",
    "71": "Spirit Breaker",
    "72": "Gyrocopter",
    "73": "Alchemist",
    "74": "Invoker",
    "75": "Silencer",
    "76": "Outworld Devourer",
    "77": "Lycan",
    "78": "Brewmaster",
    "79": "Shadow Demon",
    "80": "Lone Druid",
    "81": "Chaos Knight",
    "82": "Meepo",
    "83": "Treant Protector",
    "84": "Ogre Magi",
    "85": "Undying",
    "86": "Rubick",
    "87": "Disruptor",
    "88": "Nyx Assassin",
    "89": "Naga Siren",
    "90": "Keeper of the Light",
    "91": "Io",
    "92": "Visage",
    "93": "Slark",
    "94": "Medusa",
    "95": "Troll Warlord",
    "96": "Centaur Warrunner",
    "97": "Magnus",
    "98": "Timbersaw",
    "99": "Bristleback",
    "100": "Tusk",
    "101": "Skywrath Mage",
    "102": "Abaddon",
    "103": "Elder Titan",
    "104": "Legion Commander",
    "105": "Techies",
    "106": "Ember Spirit",
    "107": "Earth Spirit",
    "108": "Underlord",
    "109": "Terrorblade",
    "110": "Phoenix",
    "111": "Oracle",
    "112": "Winter Wyvern",
    "113": "Arc Warden",
    "114": "Monkey King",
    "119": "Dark Willow",
    "120": "Pangolier",
    "121": "Grimstroke",
    "123": "Hoodwink",
    "126": "Void Spirit",
    "128": "Snapfire",
    "129": "Mars",
    "131": "Ring Master",
    "135": "Dawnbreaker",
    "136": "Marci",
    "137": "Primal Beast",
    "138": "Muerta",
    "145": "Kez",
}

hero_mapping = {name: int(id_str) for id_str, name in raw_hero_data.items()}
id_to_name_mapping = {v: k for k, v in hero_mapping.items()}

columns_to_change = [
    "slot_0_hero_id",
    "slot_1_hero_id",
    "slot_2_hero_id",
    "slot_3_hero_id",
    "slot_4_hero_id",
    "slot_128_hero_id",
    "slot_129_hero_id",
    "slot_130_hero_id",
    "slot_131_hero_id",
    "slot_132_hero_id",
]


def upgrade() -> None:
    print("Beginning data migration: Converting hero ID strings (VARCHAR) to hero IDs (INTEGER)...")

    # Data is already numeric IDs stored as VARCHAR, so just cast to INTEGER
    for column_name in columns_to_change:
        print(f"Altering column: {column_name}")

        op.alter_column(
            "matches",
            column_name,
            existing_type=sa.VARCHAR(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using=f"{column_name}::INTEGER",
        )
    print("Data migration complete.")


def downgrade() -> None:
    print("Beginning data reversion: Converting hero IDs (INTEGER) back to hero ID strings (VARCHAR)...")

    # Convert INTEGER back to VARCHAR by casting to text
    for column_name in columns_to_change:
        print(f"Reverting column: {column_name}")

        op.alter_column(
            "matches",
            column_name,
            existing_type=sa.Integer(),
            type_=sa.VARCHAR(),
            existing_nullable=False,
            postgresql_using=f"{column_name}::VARCHAR",
        )
    print("Data reversion complete.")
