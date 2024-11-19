import requests
import time
import pandas as pd

base_url = "https://api.wiseoldman.net/v2/players/"
date_range = (
    "?startDate=2024-11-15T00%3A00%3A00.000Z&endDate=2024-11-18T23%3A59%3A00.000Z"
)

teams = {
    "Rocnars Ramblers": [
        "Pidgey Pete",
        "IronmanFrad",
        "Dewl again",
        "Gammel Mand",
        "J a i z",
        "Hecatensei",
        "protagg",
        "Teilchen",
        "Khao s",
        "Bestworrier",
        "SAN IKER",
        "WeeJos",
    ],
    "The Noobs": [
        "Conlington",
        "Roldeh",
        "T h e Theory",
        "CySneaky",
        "iFalter",
        "Papa OSRS",
        "Hexhuntar",
        "ImDevice",
        "Elysian Ring",
        "DeadCuts",
        "Its a me Emu",
        "ayyildiz",
    ],
    "Tile Snipers": [
        "Ambo the Cat",
        "Butlerone",
        "bilfeh",
        "Mjurk",
        "kim wrong un",
        "WiseOldGrant",
        "Tre Of Life",
        "JustT00Fast",
        "a n t t 1",
        "neuz",
        "Live Hash",
        "flamingotaku",
    ],
    "Leagues Waiting Room": [
        "07 Mac",
        "CeilingFan10",
        "Raathma",
        "Glm Zaal",
        "Notewoke",
        "Pires99",
        "Mr Goodfello",
        "Defig Maybe",
        "AmazingOnion",
        "MaybeRae",
        "Brklyn Mike",
        "JuicyTigr",
        "CraftyDrac",
    ],
    "Always the Nubs": [
        "7oshuaa",
        "Hoodlum Dan",
        "Brised",
        "lewee",
        "Corwin Finn",
        "Ossett",
        "I ch i",
        "Carrs Pasty",
        "Solo Gob",
        "Snakehead25",
        "Spann",
        "its me dingo",
        "lawyergirl24",
    ],
    "Who Are We": [
        "SammachLady",
        "neum",
        "Insanitas",
        "Ya",
        "Ezakhiel",
        "HCooldude505",
        "JoeWoody",
        "me is them",
        "I Suchy I",
        "V A R l",
        "Holycaw",
        "PolishGuy24",
        "Valo Ville",
    ],
    "Shadowless Monkeys": [
        "Lvl 1",
        "Solo Dani",
        "LadyArdougne",
        "Tankerton",
        "Astrayus",
        "zwangere g",
        "Event Erik",
        "Athlas X",
        "xstuart",
        "Jads Tip",
        "Phishing Sim",
        "H amme R",
        "flukeymax jr",
    ],
}

bosses = [
    "abyssal_sire",
    "artio",
    "callisto",
    "calvarion",
    "chambers_of_xeric",
    "chambers_of_xeric_challenge_mode",
    "chaos_elemental",
    "chaos_fanatic",
    "commander_zilyana",
    "crazy_archaeologist",
    "dagannoth_prime",
    "dagannoth_rex",
    "dagannoth_supreme",
    "deranged_archaeologist",
    "general_graardor",
    "kalphite_queen",
    "king_black_dragon",
    "kraken",
    "kreearra",
    "kril_tsutsaroth",
    "lunar_chests",
    "nex",
    "scorpia",
    "scurrius",
    "spindel",
    "the_gauntlet",
    "the_corrupted_gauntlet",
    "the_hueycoatl",
    "theatre_of_blood",
    "theatre_of_blood_hard_mode",
    "thermonuclear_smoke_devil",
    "tombs_of_amascut",
    "tombs_of_amascut_expert",
    "venenatis",
    "vetion",
    "vorkath",
    "zulrah",
]
skills = [
    "overall",
    "attack",
    "defence",
    "strength",
    "hitpoints",
    "ranged",
    "prayer",
    "magic",
    "thieving",
    "slayer",
    "ehp",
    "ehb",
]

kill_data = []
xp_data = []
kill_team_totals = {team: {boss: 0 for boss in bosses} for team in teams.keys()}
xp_team_totals = {team: {skill: 0 for skill in skills} for team in teams.keys()}

for team, players in teams.items():
    for player in players:
        url = base_url + player.replace(" ", "%20") + "/gained" + date_range
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            try:
                player_kills = {"Player": player, "Team": team}
                for boss in bosses:
                    kills = (
                        data["data"]["bosses"]
                        .get(boss, {})
                        .get("kills", {})
                        .get("gained", 0)
                    )
                    player_kills[boss] = kills
                    kill_team_totals[team][boss] += kills
                kill_data.append(player_kills)

                player_xp = {"Player": player, "Team": team}
                for skill in skills:
                    xp = (
                        data["data"]["skills"]
                        .get(skill, {})
                        .get("experience", {})
                        .get("gained", 0)
                    )
                    player_xp[skill] = xp
                    xp_team_totals[team][skill] += xp
                xp_data.append(player_xp)
            except KeyError:
                print(f"Data issue for player {player}")
        else:
            print(f"Failed to fetch data for: {player}")
        time.sleep(1)

kill_player_df = pd.DataFrame(kill_data)
xp_player_df = pd.DataFrame(xp_data)
kill_team_df = pd.DataFrame.from_dict(kill_team_totals, orient="index")
xp_team_df = pd.DataFrame.from_dict(xp_team_totals, orient="index")

kill_player_df.to_csv("player_kill_data.csv", index=False)
xp_player_df.to_csv("player_xp_data.csv", index=False)
kill_team_df.to_csv("team_kill_totals.csv")
xp_team_df.to_csv("team_xp_totals.csv")

print("Kill and XP data saved to separate CSV files.")
