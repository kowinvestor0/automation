"""High-retention documentary storytelling database for TikTok (>60 seconds).
Features 23 distinct real-world mysteries, engineering feats, deep ocean discoveries,
and ancient wonders. Strictly compliant with TikTok community guidelines:
100% non-violent, educational, high-retention, and ZERO duplicates across channels.
"""
from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import DATA_DIR

USED_STORIES_FILE = DATA_DIR / "used_crime_stories.json"
BLACKLIST_FILE = DATA_DIR / "blacklisted_topics.json"

# Common English words that must NEVER be used to ban topics
COMMON_EXCLUDED_WORDS = {
    "story", "the", "and", "from", "with", "this", "that", "into", "what", "most", "ever",
    "documented", "below", "your", "thoughts", "history", "science", "fascinating", "reality",
    "stranger", "fiction", "drop", "theory", "share", "friend", "comments", "unsolved",
    "ancient", "giant", "hidden", "mysterious", "temple", "buried", "space", "cosmic",
    "heist", "great", "wonder", "world", "vanished", "ocean", "discovery", "tunnel", "island",
    "breakout", "deepest", "point", "fortress", "city", "caves", "library", "figures",
    "blades", "unreinforced", "dome", "walk", "carbon", "nanotube", "theft", "made", "famous",
    "eighth", "secret", "detective", "investigation", "night", "aerial", "stone", "stones",
    "water", "under", "deep", "over", "down", "around", "first", "real", "time"
}

# Specific proper nouns and entities that have been over-posted and are STRICTLY BANNED
HISTORICAL_BANNED_ENTITIES = {
    "cooper", "alcatraz", "gardner", "roanoke", "celeste", "tunguska", "bloop", "antikythera",
    "voynich", "dyatlov", "bermuda", "dahmer", "bundy", "gacy", "ramirez", "zodiac", "massacre",
    "murder", "killer", "shakur", "bonnie", "k218b", "gotthard", "oakisland"
}

ICONIC_TRUE_CRIME_CASES: List[Dict[str, Any]] = [
    {
        "id": "great_pyramid_secret_void",
        "case_name": "The Great Pyramid Secret Void: Cosmic Ray Discovery",
        "hook_banner": "SECRET CHAMBER DETECTED \ud83d\ude31",
        "wiki_query": "ScanPyramids",
        "broll_queries": [
            "great pyramid of giza aerial sunset",
            "desert pyramid stones close up",
            "archaeology excavation laser scanning",
            "cosmic particle detector physics"
        ],
        "scenes": [
            {
                "text": "For four thousand five hundred years, historians believed the internal structure of the Great Pyramid of Giza was completely mapped.",
                "visual_hint": "broll"
            },
            {
                "text": "Built for Pharaoh Khufu, the monument stood as the tallest man-made structure on Earth for over three millennia.",
                "visual_hint": "wiki"
            },
            {
                "text": "In twenty seventeen, an international team of particle physicists deployed subatomic muon detectors around the pyramid.",
                "visual_hint": "wiki"
            },
            {
                "text": "Muons are cosmic rays that pass through stone but get absorbed by dense materials, creating an internal X-ray of the pyramid.",
                "visual_hint": "broll"
            },
            {
                "text": "What they discovered shocked the entire scientific community to its core.",
                "visual_hint": "wiki"
            },
            {
                "text": "Deep above the Grand Gallery, the detectors revealed a massive empty void at least one hundred feet long.",
                "visual_hint": "wiki"
            },
            {
                "text": "No corridors, doors, or shafts appear to lead into this sealed space from anywhere in the known structure.",
                "visual_hint": "broll"
            },
            {
                "text": "Was it built intentionally as a hidden treasury, or was it engineered to relieve pressure from the heavy stone blocks above?",
                "visual_hint": "wiki"
            },
            {
                "text": "To this day, the secret void remains completely untouched and unexplored. What do you think is sealed inside?",
                "visual_hint": "broll"
            }
        ],
        "hashtags": [
            "#pyramids",
            "#archaeology",
            "#ancientegypt",
            "#mystery",
            "#science",
            "#discovery",
            "#fyp"
        ]
    },
    {
        "id": "gobekli_tepe_sanctuary",
        "case_name": "Gobekli Tepe: The 12,000-Year-Old Megalithic Temple",
        "hook_banner": "OLDER THAN HISTORY \ud83c\udfdb\ufe0f",
        "wiki_query": "G\u00f6bekli Tepe",
        "broll_queries": [
            "ancient stone pillars excavation",
            "desert archaeological dig sunrise",
            "carved stone megalith close up",
            "turkey southeastern landscape aerial"
        ],
        "scenes": [
            {
                "text": "In nineteen ninety-four, German archaeologist Klaus Schmidt walked along a barren hilltop in southeastern Turkey.",
                "visual_hint": "broll"
            },
            {
                "text": "Beneath a layer of red soil, he noticed the tops of massive limestone pillars sticking out of the ground.",
                "visual_hint": "wiki"
            },
            {
                "text": "When excavation began, archaeologists realized they had stumbled upon something that shattered modern history.",
                "visual_hint": "broll"
            },
            {
                "text": "Gobekli Tepe dates back over eleven thousand five hundred years, making it seven thousand years older than Stonehenge.",
                "visual_hint": "wiki"
            },
            {
                "text": "Massive T-shaped pillars weighing up to sixteen tons were carved with intricate reliefs of lions, foxes, and vultures.",
                "visual_hint": "wiki"
            },
            {
                "text": "Yet this monument was constructed by nomadic hunter-gatherers who had not even developed pottery, wheels, or agriculture.",
                "visual_hint": "broll"
            },
            {
                "text": "Stranger still, after centuries of use, the entire site was deliberately backfilled and buried beneath tons of gravel by hand.",
                "visual_hint": "wiki"
            },
            {
                "text": "Why did ancient people build monumental temples before building cities, and why did they bury them? Drop your theory in the comments.",
                "visual_hint": "broll"
            }
        ],
        "hashtags": [
            "#gobeklitepe",
            "#archaeology",
            "#ancienthistory",
            "#megalith",
            "#unsolved",
            "#discovery",
            "#fyp"
        ]
    },
    {
        "id": "terracotta_army_emperor",
        "case_name": "The Terracotta Army: The Buried Underground Legion",
        "hook_banner": "8,000 BURIED SOLDIERS \u2694\ufe0f",
        "wiki_query": "Terracotta Army",
        "broll_queries": [
            "ancient terracotta warriors museum",
            "archaeological excavation trench rows",
            "ancient chinese imperial tomb",
            "dramatic lighting museum statues"
        ],
        "scenes": [
            {
                "text": "In March nineteen seventy-four, local farmers in Shaanxi, China, were digging a water well when their shovels struck terracotta shards.",
                "visual_hint": "broll"
            },
            {
                "text": "They had accidentally uncovered the grandest subterranean military installation in human history.",
                "visual_hint": "wiki"
            },
            {
                "text": "Over eight thousand life-sized terracotta soldiers, horses, and chariots stood guard in battle formation.",
                "visual_hint": "wiki"
            },
            {
                "text": "Crafted over two thousand two hundred years ago for Emperor Qin Shi Huang, each soldier possesses a completely unique facial expression.",
                "visual_hint": "broll"
            },
            {
                "text": "Ancient texts claim the central tomb of the emperor contains rivers of liquid mercury mimicking the geography of China.",
                "visual_hint": "wiki"
            },
            {
                "text": "Soil samples above the tomb confirm abnormally high mercury concentrations, and the tomb itself remains unopened.",
                "visual_hint": "broll"
            },
            {
                "text": "What treasures and traps lie inside the sealed resting place of China's first emperor? Share your thoughts below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#terracottaarmy",
            "#china",
            "#archaeology",
            "#ancienthistory",
            "#emperor",
            "#mystery",
            "#fyp"
        ]
    },
    {
        "id": "lake_vostok_antarctica",
        "case_name": "Lake Vostok: The Ancient Ocean Trapped Under Ice",
        "hook_banner": "2 MILES UNDER ICE \u2744\ufe0f",
        "wiki_query": "Lake Vostok",
        "broll_queries": [
            "antarctica ice sheet aerial freezing",
            "deep ice core drilling scientific",
            "underwater subglacial blue water",
            "extreme weather blizzard polar"
        ],
        "scenes": [
            {
                "text": "Two and a half miles beneath the coldest spot on Earth lies a secret liquid ocean that has never seen daylight.",
                "visual_hint": "broll"
            },
            {
                "text": "Lake Vostok in Antarctica is the size of Lake Ontario, sealed completely beneath a massive glacier for fifteen million years.",
                "visual_hint": "wiki"
            },
            {
                "text": "Despite temperatures dropping to minus one hundred and twenty degrees Fahrenheit on the surface, geothermal heat keeps the lake liquid.",
                "visual_hint": "broll"
            },
            {
                "text": "In twenty twelve, Russian scientists completed decades of drilling to reach the surface of the subglacial water.",
                "visual_hint": "wiki"
            },
            {
                "text": "They discovered unusual microbes and bacteria completely isolated from the rest of Earth's evolution.",
                "visual_hint": "broll"
            },
            {
                "text": "Astrobiologists study Lake Vostok to prepare for future missions searching for alien life beneath the icy crust of Jupiter's moon Europa.",
                "visual_hint": "wiki"
            },
            {
                "text": "Could ancient life-forms be thriving in the pitch-black waters miles below Antarctica? Drop your theory in the comments.",
                "visual_hint": "broll"
            }
        ],
        "hashtags": [
            "#lakevostok",
            "#antarctica",
            "#deepsea",
            "#science",
            "#aliens",
            "#discovery",
            "#fyp"
        ]
    },
    {
        "id": "kola_superdeep_borehole",
        "case_name": "The Kola Superdeep Borehole: Digging to the Deepest Point",
        "hook_banner": "40,000 FEET DOWN \ud83c\udf0b",
        "wiki_query": "Kola Superdeep Borehole",
        "broll_queries": [
            "industrial oil rig Arctic cold",
            "deep borehole drilling metal pipe",
            "molten lava core earth geological",
            "rusty abandoned research station arctic"
        ],
        "scenes": [
            {
                "text": "In nineteen seventy, Soviet geologists set out to drill deeper into the continental crust of Earth than anyone in history.",
                "visual_hint": "broll"
            },
            {
                "text": "Located on the freezing Kola Peninsula near the Arctic Circle, the drill ground through ancient crystalline rock for twenty-four years.",
                "visual_hint": "wiki"
            },
            {
                "text": "By nineteen eighty-nine, the borehole reached a staggering depth of forty thousand two hundred and thirty feet.",
                "visual_hint": "wiki"
            },
            {
                "text": "At seven miles deep, rock temperatures soared to three hundred and fifty-six degrees Fahrenheit, behaving more like plastic than stone.",
                "visual_hint": "broll"
            },
            {
                "text": "Unexpectedly, scientists found microscopic plankton fossils sealed four miles beneath the surface and boiling water circulating through deep fractures.",
                "visual_hint": "wiki"
            },
            {
                "text": "When the drill bit repeatedly melted in the scorching heat, drilling was permanently halted in nineteen ninety-four.",
                "visual_hint": "broll"
            },
            {
                "text": "Today, the deepest artificial hole on Earth is welded shut with a steel cap. What lies beneath Earth's deepest crust? Comment below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#kolaborehole",
            "#geology",
            "#earthscience",
            "#deepestpoint",
            "#mystery",
            "#history",
            "#fyp"
        ]
    },
    {
        "id": "cave_of_crystals_naica",
        "case_name": "The Cave of Crystals: Naica's Giant Underground Megacrystals",
        "hook_banner": "GIANT CRYSTAL FORTRESS \ud83d\udc8e",
        "wiki_query": "Cave of the Crystals",
        "broll_queries": [
            "underground crystal cave selenite pillars",
            "geologist explorer subterranean flashlight",
            "underground magma chamber steam glowing",
            "dramatic minerals cavern geological"
        ],
        "scenes": [
            {
                "text": "A thousand feet below the Chihuahuan desert in Mexico lies an alien landscape straight out of a science fiction movie.",
                "visual_hint": "broll"
            },
            {
                "text": "In the year two thousand, miners pumping water from the Naica lead-zinc mine broke into an astonishing subterranean chamber.",
                "visual_hint": "wiki"
            },
            {
                "text": "Inside, giant selenite gypsum beams up to thirty-nine feet long and weighing fifty-five tons crossed the chamber.",
                "visual_hint": "wiki"
            },
            {
                "text": "For five hundred thousand years, magma chambers beneath kept the mineral-rich groundwater at a constant one hundred and thirty-six degrees.",
                "visual_hint": "broll"
            },
            {
                "text": "Human beings can only survive inside for ten minutes without cooling suits before their lungs begin to condense moisture.",
                "visual_hint": "wiki"
            },
            {
                "text": "Scientists discovered dormant ancient bacteria inside the crystals that had survived for over fifty thousand years.",
                "visual_hint": "broll"
            },
            {
                "text": "Now flooded again with water, the crystals will continue growing in the dark for eternity. Would you step foot inside? Comment below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#crystals",
            "#caveofcrystals",
            "#naica",
            "#geology",
            "#earth",
            "#discovery",
            "#fyp"
        ]
    },
    {
        "id": "wow_signal_deep_space",
        "case_name": "The Wow! Signal: The 72-Second Cosmic Broadcast",
        "hook_banner": "MESSAGE FROM SPACE? \ud83d\udce1",
        "wiki_query": "Wow! signal",
        "broll_queries": [
            "giant radio telescope array night stars",
            "computer terminal green text vintage",
            "deep space spiral galaxy nebula",
            "astronomer observatory night listening"
        ],
        "scenes": [
            {
                "text": "On August fifteenth, nineteen seventy-seven, astronomer Jerry Ehman was reviewing computer printouts from the Big Ear radio telescope in Ohio.",
                "visual_hint": "broll"
            },
            {
                "text": "Suddenly, a sequence of characters on the paper caught his eye: six, E, Q, U, J, five.",
                "visual_hint": "wiki"
            },
            {
                "text": "The signal was thirty times louder than background deep space noise and broadcast at exactly one thousand four hundred and twenty megahertz.",
                "visual_hint": "wiki"
            },
            {
                "text": "This frequency corresponds to the hydrogen line, the universal communication channel expected by scientists searching for extraterrestrial intelligence.",
                "visual_hint": "broll"
            },
            {
                "text": "The transmission lasted exactly seventy-two seconds, the precise duration Big Ear's antenna took to sweep past that coordinate.",
                "visual_hint": "wiki"
            },
            {
                "text": "Ehman circled the sequence in red ink and wrote the word 'Wow!' in the margin.",
                "visual_hint": "wiki"
            },
            {
                "text": "Despite dozens of astronomical surveys scanning the same patch of space in Sagittarius over five decades, the signal never returned.",
                "visual_hint": "broll"
            },
            {
                "text": "Was it an alien transmission or a natural cosmic phenomenon? Drop your theory in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#wowsignal",
            "#seti",
            "#astronomy",
            "#space",
            "#aliens",
            "#unsolved",
            "#fyp"
        ]
    },
    {
        "id": "voyager_1_interstellar",
        "case_name": "Voyager 1: The Human Messenger in Interstellar Space",
        "hook_banner": "15 BILLION MILES AWAY \ud83d\ude80",
        "wiki_query": "Voyager 1",
        "broll_queries": [
            "deep space probe voyager spacecraft 3d",
            "earth pale blue dot distant space",
            "solar system edge interstellar space",
            "golden record phonograph space probe"
        ],
        "scenes": [
            {
                "text": "Launched in September nineteen seventy-seven, Voyager One was built to operate for just five years exploring Jupiter and Saturn.",
                "visual_hint": "broll"
            },
            {
                "text": "Today, nearly five decades later, it is the farthest human-made object in history, cruising fifteen billion miles from Earth.",
                "visual_hint": "wiki"
            },
            {
                "text": "In twenty twelve, Voyager crossed the heliopause, leaving the sun's magnetic bubble to enter the true interstellar void.",
                "visual_hint": "wiki"
            },
            {
                "text": "Carried on its side is the Golden Record, a gold-plated copper phonograph carrying Earth sounds, music, and human greetings.",
                "visual_hint": "broll"
            },
            {
                "text": "Radio signals traveling at the speed of light take over twenty-two hours to make the one-way journey back to NASA antennas.",
                "visual_hint": "wiki"
            },
            {
                "text": "Long after humanity is gone, Voyager One will drift silently through the Milky Way galaxy for billions of years.",
                "visual_hint": "broll"
            },
            {
                "text": "What would an alien civilization think if they intercepted Voyager One? Share your thoughts below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#voyager1",
            "#nasa",
            "#space",
            "#astronomy",
            "#goldenrecord",
            "#science",
            "#fyp"
        ]
    },
    {
        "id": "saturn_hexagon_storm",
        "case_name": "Saturn's Hexagon: The Geometric Cloud Jet Stream",
        "hook_banner": "HEXAGON ON SATURN \ud83e\ude90",
        "wiki_query": "Saturn's hexagon",
        "broll_queries": [
            "planet saturn rings space telescope",
            "geometric hexagon storm saturn pole",
            "atmospheric hurricane swirling storm vortex",
            "deep space exploration spacecraft footage"
        ],
        "scenes": [
            {
                "text": "When Voyager One flew past Saturn in nineteen eighty, scientists noticed an impossible geometric shape at the planet's north pole.",
                "visual_hint": "broll"
            },
            {
                "text": "Later confirmed by the Cassini spacecraft, a perfect six-sided polygon spans twenty thousand miles across the clouds.",
                "visual_hint": "wiki"
            },
            {
                "text": "Each side of this colossal hexagon is larger than the diameter of Earth, with atmospheric jet streams blowing at two hundred miles per hour.",
                "visual_hint": "wiki"
            },
            {
                "text": "At its center swirls a massive hurricane with an eye fifty times larger than any hurricane ever seen on Earth.",
                "visual_hint": "broll"
            },
            {
                "text": "Laboratory physicists discovered that spinning fluid tanks can create geometric polygons due to shear wave differences.",
                "visual_hint": "wiki"
            },
            {
                "text": "Yet Saturn's hexagon has remained stable for over forty years, changing color from blue to gold with Saturn's seasons.",
                "visual_hint": "broll"
            },
            {
                "text": "How can nature form a perfect geometric shape in planetary clouds? Drop your reaction in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#saturn",
            "#hexagon",
            "#astronomy",
            "#space",
            "#cassini",
            "#nasa",
            "#fyp"
        ]
    },
    {
        "id": "richat_structure_sahara",
        "case_name": "The Richat Structure: The Mysterious Eye of the Sahara",
        "hook_banner": "THE EYE OF THE SAHARA \ud83d\udc41\ufe0f",
        "wiki_query": "Richat Structure",
        "broll_queries": [
            "sahara desert sand dunes aerial golden",
            "richat structure satellite view geological rings",
            "astronaut looking out space station window",
            "desert rock geological formations canyon"
        ],
        "scenes": [
            {
                "text": "From high above in orbit, astronauts look down on the Sahara Desert of Mauritania and see a giant concentric bullseye.",
                "visual_hint": "broll"
            },
            {
                "text": "Known as the Richat Structure, or the Eye of the Sahara, this geological formation stretches twenty-five miles in diameter.",
                "visual_hint": "wiki"
            },
            {
                "text": "Early geologists suspected it was a giant meteorite impact crater due to its circular symmetry.",
                "visual_hint": "broll"
            },
            {
                "text": "However, field expeditions found no shocked quartz or extraterrestrial rock fragments.",
                "visual_hint": "wiki"
            },
            {
                "text": "Geologists now believe it is an eroded geological dome pushed upward by molten magma one hundred million years ago.",
                "visual_hint": "broll"
            },
            {
                "text": "Alternative theorists frequently compare its dimensions and concentric rings to Plato's description of the lost city of Atlantis.",
                "visual_hint": "wiki"
            },
            {
                "text": "Whether a natural geological dome or an ancient enigma, the Eye of the Sahara remains one of Earth's greatest visual spectacles.",
                "visual_hint": "broll"
            }
        ],
        "hashtags": [
            "#eyeofthesahara",
            "#richatstructure",
            "#geology",
            "#sahara",
            "#mystery",
            "#earth",
            "#fyp"
        ]
    },
    {
        "id": "darvaza_gas_crater",
        "case_name": "The Door to Hell: Darvaza's 50-Year Burning Gas Crater",
        "hook_banner": "BURNING FOR 50 YEARS \ud83d\udd25",
        "wiki_query": "Darvaza gas crater",
        "broll_queries": [
            "karakum desert turkmenistan sand dunes",
            "darvaza gas crater burning fire pit night",
            "geologists expedition extreme heat crater",
            "desert night sky stars glowing flames"
        ],
        "scenes": [
            {
                "text": "In the middle of the Karakum Desert in Turkmenistan burns a giant flaming crater two hundred and thirty feet wide.",
                "visual_hint": "broll"
            },
            {
                "text": "Known as the Door to Hell, this fiery pit has been roaring continuously for over fifty years without stopping.",
                "visual_hint": "wiki"
            },
            {
                "text": "In nineteen seventy-one, Soviet engineers were drilling for oil when the ground beneath their rig collapsed into an underground natural gas cavern.",
                "visual_hint": "wiki"
            },
            {
                "text": "Fearing poisonous methane would drift into neighboring villages, geologists decided to ignite the gas, expecting it to burn out in a few weeks.",
                "visual_hint": "broll"
            },
            {
                "text": "Instead, the subterranean gas pockets proved virtually bottomless, and the flames have burned non-stop ever since.",
                "visual_hint": "wiki"
            },
            {
                "text": "In twenty thirteen, explorer George Kourounis became the first person to rappel four hundred feet down into the blazing inferno.",
                "visual_hint": "broll"
            },
            {
                "text": "At the fiery bottom, he discovered extremophile bacteria living happily inside the scorching soil.",
                "visual_hint": "wiki"
            },
            {
                "text": "Would you stand on the edge of the Door to Hell? Drop your reaction in the comments.",
                "visual_hint": "broll"
            }
        ],
        "hashtags": [
            "#doortohell",
            "#darvaza",
            "#geology",
            "#firecrater",
            "#mystery",
            "#earth",
            "#fyp"
        ]
    },
    {
        "id": "mauritius_underwater_fall",
        "case_name": "The Underwater Waterfall of Mauritius: The Ocean Floor Abyss",
        "hook_banner": "UNDERWATER WATERFALL \ud83c\udf0a",
        "wiki_query": "Mauritius",
        "broll_queries": [
            "mauritius island turquoise lagoon aerial",
            "underwater waterfall illusion sand runoff ocean",
            "crystal clear tropical ocean reef waves",
            "deep ocean continental shelf dropoff blue"
        ],
        "scenes": [
            {
                "text": "Off the southwestern tip of the tropical island of Mauritius lies one of Earth's most breathtaking optical illusions.",
                "visual_hint": "broll"
            },
            {
                "text": "From an airplane, the turquoise ocean floor suddenly plunges into a gigantic, swirling subterranean abyss.",
                "visual_hint": "wiki"
            },
            {
                "text": "It looks exactly like a colossal underwater waterfall cascading thousands of feet into the ocean deep.",
                "visual_hint": "wiki"
            },
            {
                "text": "Despite appearances, water is not falling; the phenomenon is driven by shifting underwater sand currents.",
                "visual_hint": "broll"
            },
            {
                "text": "Waves constantly push sand and silt off the shallow coastal plateau into an oceanic drop-off two and a half miles deep.",
                "visual_hint": "wiki"
            },
            {
                "text": "The changing shades of turquoise, emerald, and dark midnight blue create the convincing illusion of a plummeting cataract.",
                "visual_hint": "broll"
            },
            {
                "text": "One of the most spectacular aerial views on planet Earth. Share this with someone who needs to see it!",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#mauritius",
            "#underwaterwaterfall",
            "#ocean",
            "#earth",
            "#nature",
            "#travel",
            "#fyp"
        ]
    },
    {
        "id": "trappist_1_exoplanets",
        "case_name": "TRAPPIST-1: The 7 Earth-Sized Worlds Around One Star",
        "hook_banner": "7 EARTH-SIZED PLANETS \ud83e\ude90",
        "wiki_query": "TRAPPIST-1",
        "broll_queries": [
            "trappist 1 exoplanet system orbit 3d",
            "red dwarf star ultra cool deep space",
            "james webb space telescope golden mirrors",
            "alien planet surface ocean landscape sunset"
        ],
        "scenes": [
            {
                "text": "Forty light-years away in the constellation Aquarius lies the most promising alien solar system ever discovered.",
                "visual_hint": "broll"
            },
            {
                "text": "Orbiting an ultra-cool red dwarf star called TRAPPIST-One are seven rocky, Earth-sized planets packed tightly together.",
                "visual_hint": "wiki"
            },
            {
                "text": "Three of these worlds orbit within the star's habitable zone where liquid water could pool on their surfaces.",
                "visual_hint": "wiki"
            },
            {
                "text": "The planets orbit so close to one another that standing on one surface, neighboring worlds would appear larger in the sky than our full moon.",
                "visual_hint": "broll"
            },
            {
                "text": "In twenty twenty-three, NASA's James Webb Space Telescope began analyzing the atmospheric compositions of these alien planets.",
                "visual_hint": "wiki"
            },
            {
                "text": "If life evolved on one planet, interplanetary meteorites could easily seed life across all seven sister worlds.",
                "visual_hint": "broll"
            },
            {
                "text": "Could alien civilizations be looking back at us from TRAPPIST-One? Drop your thoughts in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#trappist1",
            "#exoplanets",
            "#space",
            "#nasa",
            "#jameswebb",
            "#aliens",
            "#fyp"
        ]
    },
    {
        "id": "james_webb_first_galaxies",
        "case_name": "The James Webb Telescope: Finding the First Galaxies of Time",
        "hook_banner": "DAWN OF THE UNIVERSE \ud83d\udd2d",
        "wiki_query": "James Webb Space Telescope",
        "broll_queries": [
            "james webb space telescope deep space deploy",
            "deep field galaxies cosmic infrared colors",
            "rocket launch ariane 5 french guiana",
            "cosmic big bang universe expansion 3d"
        ],
        "scenes": [
            {
                "text": "Stationed one million miles from Earth at the Second Lagrange Point, the James Webb Space Telescope looks backward in time.",
                "visual_hint": "broll"
            },
            {
                "text": "Equipped with a twenty-one-foot gold-coated beryllium mirror, Webb sees infrared light emitted over thirteen billion years ago.",
                "visual_hint": "wiki"
            },
            {
                "text": "Within weeks of launching scientific operations, Webb shattered cosmological models by discovering fully formed, massive galaxies.",
                "visual_hint": "wiki"
            },
            {
                "text": "These galaxies existed just three hundred million years after the Big Bang, far earlier and larger than standard physics predicted.",
                "visual_hint": "broll"
            },
            {
                "text": "The discoveries are forcing astrophysicists to completely rethink how the earliest stars, black holes, and galaxies formed.",
                "visual_hint": "wiki"
            },
            {
                "text": "Webb is peering into the cosmic dawn, capturing the moment the very first light illuminated the universe.",
                "visual_hint": "broll"
            },
            {
                "text": "What cosmic secrets will Webb uncover next? Drop your reaction in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#jameswebb",
            "#jwst",
            "#space",
            "#astronomy",
            "#nasa",
            "#universe",
            "#fyp"
        ]
    },
    {
        "id": "mariana_snailfish_record",
        "case_name": "The Mariana Snailfish: The Deepest Living Fish on Earth",
        "hook_banner": "27,000 FEET DEEP \ud83d\udc1f",
        "wiki_query": "Mariana snailfish",
        "broll_queries": [
            "deep ocean submarine submersible abyss lights",
            "mariana snailfish swimming deep sea floor",
            "underwater hydrothermal vent bubbles pressure",
            "deep oceanic trench bathymetry mapping"
        ],
        "scenes": [
            {
                "text": "Five miles beneath the Pacific Ocean surface in the Mariana Trench, the water pressure is one thousand times greater than at sea level.",
                "visual_hint": "broll"
            },
            {
                "text": "That is equivalent to having sixteen hundred elephants standing on the roof of a small passenger car.",
                "visual_hint": "wiki"
            },
            {
                "text": "Yet swimming peacefully in this freezing, pitch-black abyss is the Mariana snailfish, the deepest living vertebrate known to science.",
                "visual_hint": "wiki"
            },
            {
                "text": "Its skin is completely translucent, and its bones are made of flexible cartilage rather than rigid calcium to prevent crushing.",
                "visual_hint": "broll"
            },
            {
                "text": "Its cells produce high concentrations of trimethylamine oxide, a special chemical that prevents proteins from collapsing under pressure.",
                "visual_hint": "wiki"
            },
            {
                "text": "In twenty twenty-three, Japanese researchers filmed a snailfish swimming at an astounding depth of twenty-seven thousand three hundred and forty-nine feet.",
                "visual_hint": "broll"
            },
            {
                "text": "Life thrives in the most extreme environments on planet Earth. What else is hiding down there? Comment below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#marianatrench",
            "#snailfish",
            "#deepsea",
            "#ocean",
            "#biology",
            "#earth",
            "#fyp"
        ]
    },
    {
        "id": "woolly_mammoth_revival",
        "case_name": "The Woolly Mammoth Revival: Bringing Extinction Back to Life",
        "hook_banner": "DE-EXTINCTION IS REAL \ud83e\udda3",
        "wiki_query": "De-extinction",
        "broll_queries": [
            "siberian tundra permafrost snowy landscape",
            "woolly mammoth fossil skeleton museum",
            "crispr gene editing laboratory biotechnology",
            "arctic tundra mammoth grazing cgi realistic"
        ],
        "scenes": [
            {
                "text": "Four thousand years ago, the very last herd of woolly mammoths died out on isolated Wrangel Island in the Arctic Ocean.",
                "visual_hint": "broll"
            },
            {
                "text": "For millennia, their frozen carcasses remained preserved in the Siberian permafrost with hair, skin, and bone marrow intact.",
                "visual_hint": "wiki"
            },
            {
                "text": "Today, geneticists using advanced CRISPR gene-editing tools are extracting viable DNA to resurrect the ancient titan.",
                "visual_hint": "wiki"
            },
            {
                "text": "By inserting mammoth cold-resistant genes into the Asian elephant genome, scientists are creating a cold-tolerant mammoth-elephant hybrid.",
                "visual_hint": "broll"
            },
            {
                "text": "Biologists argue that reintroducing mammoths to the Arctic tundra will compact snow, prevent permafrost melting, and trap greenhouse gases.",
                "visual_hint": "wiki"
            },
            {
                "text": "Biotech companies project the first resurrected mammoth calves could be born before the end of this decade.",
                "visual_hint": "broll"
            },
            {
                "text": "Should humanity bring back extinct Ice Age creatures, or are we playing with fire? Drop your opinion below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#woollymammoth",
            "#deextinction",
            "#genetics",
            "#science",
            "#iceage",
            "#crispr",
            "#fyp"
        ]
    },
    {
        "id": "oumuamua_interstellar_object",
        "case_name": "Oumuamua: The Mysterious Cigar-Shaped Interstellar Visitor",
        "hook_banner": "FIRST ALIEN VISITOR? \ud83d\ude80",
        "wiki_query": "\u02bbOumuamua",
        "broll_queries": [
            "cigar shaped interstellar asteroid space 3d",
            "telescope observatory hawaii summit dome",
            "solar system trajectory slingshot sun orbit",
            "deep space artist concept alien technology"
        ],
        "scenes": [
            {
                "text": "In October twenty seventeen, the Pan-STARRS telescope in Hawaii spotted a faint object tumbling rapidly through our solar system.",
                "visual_hint": "broll"
            },
            {
                "text": "Traveling at nearly two hundred thousand miles per hour, its hyperbolic trajectory proved it originated from outside our solar system.",
                "visual_hint": "wiki"
            },
            {
                "text": "It was named Oumuamua, a Hawaiian word meaning 'scout reaching out from the distant past.'",
                "visual_hint": "wiki"
            },
            {
                "text": "Light curve analysis showed it was ten times longer than it was wide, shaped like a colossal cigar or flattened pancake.",
                "visual_hint": "broll"
            },
            {
                "text": "As it swung past the sun, it accelerated outward without producing any visible comet dust or outgassing.",
                "visual_hint": "wiki"
            },
            {
                "text": "Harvard astrophysicist Avi Loeb proposed the controversial theory that Oumuamua was an artificial alien solar sail light-craft.",
                "visual_hint": "broll"
            },
            {
                "text": "Oumuamua has now vanished back into deep interstellar space, its true nature an eternal mystery. What was it? Comment below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#oumuamua",
            "#interstellar",
            "#space",
            "#astronomy",
            "#aliens",
            "#harvard",
            "#fyp"
        ]
    },
    {
        "id": "black_hole_event_horizon",
        "case_name": "The Event Horizon: Photographing a Real Supermassive Black Hole",
        "hook_banner": "SEEING THE UNSEEABLE \ud83d\udd73\ufe0f",
        "wiki_query": "Event Horizon Telescope",
        "broll_queries": [
            "event horizon black hole orange glowing ring",
            "radio telescope observatory atacama alma desert",
            "supercomputer data center server racks glowing",
            "galaxy messier 87 core relativistic jet"
        ],
        "scenes": [
            {
                "text": "For over a century, physicists believed taking a real photograph of a black hole was physically impossible.",
                "visual_hint": "broll"
            },
            {
                "text": "Because their gravitational pull is so intense that not even light can escape, a black hole is completely invisible.",
                "visual_hint": "wiki"
            },
            {
                "text": "In April twenty nineteen, the Event Horizon Telescope collaboration synchronized eight radio telescopes across four continents.",
                "visual_hint": "wiki"
            },
            {
                "text": "By linking observatories from the South Pole to Hawaii, they created a virtual telescope as large as planet Earth.",
                "visual_hint": "broll"
            },
            {
                "text": "They targeted the supermassive black hole at the center of galaxy Messier Eighty-Seven, fifty-five million light-years away.",
                "visual_hint": "wiki"
            },
            {
                "text": "The resulting historic image revealed a glowing ring of superheated gas bent around a pitch-black shadow six billion times heavier than our sun.",
                "visual_hint": "broll"
            },
            {
                "text": "Albert Einstein's general theory of relativity was proven right once again. Share this incredible feat of human engineering!",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#blackhole",
            "#eventhorizon",
            "#physics",
            "#einstein",
            "#astronomy",
            "#space",
            "#fyp"
        ]
    },
    {
        "id": "sutton_hoo_ship_burial",
        "case_name": "Sutton Hoo: The Anglo-Saxon Royal Ship Burial in Gold",
        "hook_banner": "KING OF ANCIENT GOLD \ud83d\udc51",
        "wiki_query": "Sutton Hoo",
        "broll_queries": [
            "english countryside grassy burial mounds misty",
            "sutton hoo iron helmet replica museum",
            "archaeological excavation ship timber rivets",
            "anglo saxon gold garnet jewelry sparkling"
        ],
        "scenes": [
            {
                "text": "In the summer of nineteen thirty-nine, on the eve of World War Two, a landowner in Suffolk, England, asked an amateur archaeologist to dig into strange grassy mounds.",
                "visual_hint": "broll"
            },
            {
                "text": "Beneath Mound One, Basil Brown uncovered the ghost impression of an eighty-eight-foot wooden Anglo-Saxon warship.",
                "visual_hint": "wiki"
            },
            {
                "text": "At the center of the ship lay an untouched seventh-century royal burial chamber filled with glittering treasures.",
                "visual_hint": "wiki"
            },
            {
                "text": "Gold shoulder clasps inlaid with Sri Lankan garnets, silver banquet plates from Constantinople, and the iconic iron masked helmet were unearthed.",
                "visual_hint": "broll"
            },
            {
                "text": "The discovery revolutionized history, proving Anglo-Saxon Britain was not an uncivilized Dark Age, but a sophisticated global trading power.",
                "visual_hint": "wiki"
            },
            {
                "text": "Curiously, not a single bone of the king was ever found inside the ship burial chamber.",
                "visual_hint": "broll"
            },
            {
                "text": "Who was the mighty king laid to rest inside this subterranean warship? Drop your theory in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#suttonhoo",
            "#archaeology",
            "#history",
            "#anglosaxon",
            "#treasure",
            "#mystery",
            "#fyp"
        ]
    },
    {
        "id": "marfa_lights_texas",
        "case_name": "The Marfa Lights: The Desert Mystery That Baffles Science",
        "hook_banner": "GLOWING DESERT ORBS \ud83d\udca1",
        "wiki_query": "Marfa lights",
        "broll_queries": [
            "west texas desert highway night starry",
            "glowing colored light orbs desert horizon",
            "night vision binoculars looking desert hills",
            "chinati mountains southwest desert landscape"
        ],
        "scenes": [
            {
                "text": "Just outside the small desert town of Marfa in West Texas, strange nocturnal lights have appeared for over a century.",
                "visual_hint": "broll"
            },
            {
                "text": "First recorded by cowhand Robert Ellison in eighteen eighty-three, observers witness basketball-sized glowing orbs hovering above the desert.",
                "visual_hint": "wiki"
            },
            {
                "text": "The lights appear in yellow, orange, and blue, dancing across the Mitchell Flat plains and darting through the air.",
                "visual_hint": "wiki"
            },
            {
                "text": "They split in two, merge together, hover motionless, and then vanish into thin air.",
                "visual_hint": "broll"
            },
            {
                "text": "Scientists and military surveys have installed automated cameras, spectrometers, and radar stations to crack the mystery.",
                "visual_hint": "wiki"
            },
            {
                "text": "While some lights are atmospheric mirages of highway car headlights, historical sightings occurred long before cars or electricity existed.",
                "visual_hint": "broll"
            },
            {
                "text": "Are they piezoelectric earth lights, desert mirages, or something unexplainable? Share your thoughts below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#marfalights",
            "#texas",
            "#unsolvedmysteries",
            "#paranormal",
            "#science",
            "#nightsky",
            "#fyp"
        ]
    },
    {
        "id": "catatumbo_lightning_storm",
        "case_name": "Catatumbo Lightning: The Never-Ending Thunderstorm",
        "hook_banner": "THE ENDLESS STORM \u26a1",
        "wiki_query": "Catatumbo lightning",
        "broll_queries": [
            "lake maracaibo venezuela lightning night",
            "multiple lightning strikes dark stormy sky",
            "storm clouds glowing purple lightning flash",
            "tropical lake water reflections lightning"
        ],
        "scenes": [
            {
                "text": "Over Lake Maracaibo in northwestern Venezuela, the sky ignites in an endless atmospheric war.",
                "visual_hint": "broll"
            },
            {
                "text": "For up to three hundred nights a year, ten hours a night, lightning strikes the marshlands up to twenty-eight times per minute.",
                "visual_hint": "wiki"
            },
            {
                "text": "Known as the Catatumbo Lightning, it produces over one million electrical discharges annually, making it the lightning capital of the world.",
                "visual_hint": "wiki"
            },
            {
                "text": "The flashes are so intense and continuous that Caribbean sailors used the glow as a natural lighthouse for four hundred years.",
                "visual_hint": "broll"
            },
            {
                "text": "Warm, humid Caribbean winds clash against cool air from the surrounding Andes mountains, creating an eternal thunderhead factory.",
                "visual_hint": "wiki"
            },
            {
                "text": "Methane gas rising from the deep swamps also acts as a natural ionized fuel enhancing the electrical conductivity.",
                "visual_hint": "broll"
            },
            {
                "text": "Would you stand beneath the most electrified sky on Earth? Drop your reaction in the comments.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#catatumbo",
            "#lightning",
            "#weather",
            "#venezuela",
            "#nature",
            "#science",
            "#fyp"
        ]
    },
    {
        "id": "archimedes_claw_machine",
        "case_name": "The Claw of Archimedes: The Ancient Ship-Lifting Weapon",
        "hook_banner": "ANCIENT WAR MACHINE \u2699\ufe0f",
        "wiki_query": "Claw of Archimedes",
        "broll_queries": [
            "ancient greek galley warships sea waves",
            "syracuse sicily coastal fortress stone walls",
            "ancient wooden crane gear lever mechanism 3d",
            "historical naval siege roman catapults"
        ],
        "scenes": [
            {
                "text": "In two hundred and thirteen BC, a massive Roman fleet sailed into the harbor of Syracuse, expecting an easy conquest.",
                "visual_hint": "broll"
            },
            {
                "text": "Instead, they were confronted by the technological genius of the great mathematician Archimedes.",
                "visual_hint": "wiki"
            },
            {
                "text": "Positioned atop the seawall was the Iron Hand, or the Claw of Archimedes: a titanic grappling beam crane.",
                "visual_hint": "wiki"
            },
            {
                "text": "As Roman quinqueremes approached the city walls, giant iron claws dropped from the sky, snagged the bow of the ships, and hoisted them straight out of the water.",
                "visual_hint": "broll"
            },
            {
                "text": "Using advanced leverage and counterweights, the operators shook the warship violently, dumping soldiers into the sea, before dropping the ship to smash on the rocks.",
                "visual_hint": "wiki"
            },
            {
                "text": "Roman crews were so terrified of Archimedes's defense machines that if they saw a single rope hanging over the wall, they retreated in panic.",
                "visual_hint": "broll"
            },
            {
                "text": "Ancient engineering was far more advanced than we were taught in school. Share your thoughts below!",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#archimedes",
            "#ancientgreece",
            "#engineering",
            "#history",
            "#warmachine",
            "#science",
            "#fyp"
        ]
    },
    {
        "id": "great_blue_hole_belize",
        "case_name": "The Great Blue Hole: The 400-Foot Vertical Marine Sinkhole",
        "hook_banner": "400-FOOT OCEAN SINKHOLE \ud83d\udd73\ufe0f",
        "wiki_query": "Great Blue Hole",
        "broll_queries": [
            "great blue hole belize aerial circular reef",
            "scuba diver descending dark blue abyss",
            "underwater stalactites submerged cave ancient",
            "caribbean coral reef marine life turquoise"
        ],
        "scenes": [
            {
                "text": "Sixty miles off the coast of Belize in the center of Lighthouse Reef lies a near-perfect circular marine sinkhole.",
                "visual_hint": "broll"
            },
            {
                "text": "The Great Blue Hole measures nearly one thousand feet across and plunges vertically down over four hundred feet.",
                "visual_hint": "wiki"
            },
            {
                "text": "During the last Ice Age, this was an enormous dry limestone cave system above sea level.",
                "visual_hint": "wiki"
            },
            {
                "text": "As glaciers melted and oceans rose, the cave roof collapsed and was submerged under the rising Caribbean Sea.",
                "visual_hint": "broll"
            },
            {
                "text": "At a depth of one hundred and thirty feet, divers encounter giant submerged stalactites up to twenty feet long, frozen in time.",
                "visual_hint": "wiki"
            },
            {
                "text": "Below three hundred feet, a thick layer of toxic hydrogen sulfide blocks all oxygen and light, leaving the bottom completely devoid of life.",
                "visual_hint": "broll"
            },
            {
                "text": "Would you scuba dive into the black depths of the Great Blue Hole? Comment below.",
                "visual_hint": "wiki"
            }
        ],
        "hashtags": [
            "#greatbluehole",
            "#belize",
            "#ocean",
            "#diving",
            "#geology",
            "#earth",
            "#fyp"
        ]
    }
]


def load_used_story_ids() -> List[str]:
    """Loads list of story IDs that have already been produced."""
    if USED_STORIES_FILE.exists():
        try:
            return json.loads(USED_STORIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_used_story_ids(used_ids: List[str]) -> None:
    """Saves used story IDs to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USED_STORIES_FILE.write_text(json.dumps(used_ids, indent=2), encoding="utf-8")


def load_all_blacklisted_keywords() -> List[str]:
    """Loads specific banned entity keywords, filtering out common words."""
    keywords = set(HISTORICAL_BANNED_ENTITIES)
    if BLACKLIST_FILE.exists():
        try:
            data = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
            for kw in data.get("keywords", []):
                clean_kw = kw.lower().strip()
                if len(clean_kw) > 3 and clean_kw not in COMMON_EXCLUDED_WORDS:
                    keywords.add(clean_kw)
        except Exception:
            pass
    return list(keywords)


def generate_dynamic_crime_story(
    used_ids: List[str],
    forbidden_keywords: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """Generates a completely new real documentary story via Gemini with rate limit guard.
    Strictly complies with TikTok Guidelines: 100% G-rated / educational / high retention.
    Actively avoids topics matching forbidden_keywords to guarantee zero repetition.
    """
    try:
        from core.config_manager import get_api_key
        import requests
        key = get_api_key("gemini_api_key")
        if not key or len(key) < 20:
            return None

        categories = [
            "Breathtaking Scientific Discovery & Deep Space Exploration (NASA, James Webb, Deep Cosmos, Black Holes, Exoplanets)",
            "Deep Ocean Exploration & Unexplained Marine Phenomenon (Mariana Trench, Abyssal Plain, Hydrothermal Vents, Bioluminescence)",
            "Mega Engineering Marvel & Impossible Construction Feats (Megastructures, Underground Tunnels, Transcontinental Rails, Panama Canal)",
            "Lost Ancient Civilizations & Archaeological Discoveries (Pyramids of Giza, Petra, Machu Picchu, Terracotta Army, Gobekli Tepe)",
            "Extreme Weather, Geological Oddities & Bizarre Natural Phenomena (Rogue Waves, Supervolcanoes, Sailing Stones, Giant Sinkholes)",
            "Famous Non-Violent Historical Enigmas, Crypto-Mysteries & Lost Treasures (Beale Ciphers, Amber Room, Antikythera Mechanism)",
            "Pioneering Aviation & Arctic/Polar Expedition Feats (Amundsen South Pole, Apollo Missions, Deep Sea Submersibles)",
            "Prehistoric Earth & Paleontological Wonders (Fossil Discoveries, Megalodon, Woolly Mammoth Discovery, Ancient Giant Flora)",
            "Ancient Architectural & Engineering Genius (Roman Aqueducts, Incan Masonry, Ancient Water Clocks, Nan Madol)",
            "Bizarre Physics Phenomena & Laboratory Discoveries (Superfluidity, Particle Colliders, Quantum Entanglement Experiments)"
        ]
        chosen_cat = random.choice(categories)

        # Build anti-duplication clause from forbidden keywords
        forbidden_clause = ""
        if forbidden_keywords:
            clean_kw = [k.strip() for k in forbidden_keywords if len(k.strip()) > 3 and k.strip() not in COMMON_EXCLUDED_WORDS]
            if clean_kw:
                forbidden_clause = f"\n4. AVOID REPETITION: Under no circumstances choose topics related to any of these recently used keywords: {', '.join(clean_kw[:25])}."

        prompt = (
            f"Generate 1 high-retention viral documentary topic in the category: '{chosen_cat}'.\n"
            f"Requirements:\n"
            f"1. Must have a real, verified Wikipedia article with public domain historical photos.\n"
            f"2. STRICT TIKTOK COMMUNITY GUIDELINES: Absolutely NO graphic violence, gore, murders, serial killers, weapons, politics, or controversy. 100% safe for all audiences.\n"
            f"3. High viral intrigue and educational fascination.{forbidden_clause}\n"
            f"Return JSON format:\n"
            f'{{\"id\": \"unique_id\", \"case_name\": \"Full Title\", \"hook_banner\": \"ALL CAPS 3-5 WORDS\", '
            f'\"wiki_query\": \"Exact Wikipedia Title\", '
            f'\"broll_queries\": [\"cinematic ocean aerial\", \"astronomy telescope night\"], '
            f'\"scenes\": [{{\"text\": \"Deep beneath the surface...\", \"visual_hint\": \"wiki\"}}], '
            f'\"hashtags\": [\"#science\", \"#discovery\", \"#mindblown\", \"#fyp\"]}}'
        )
        models_to_try = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
        for mod in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.95,
                }
            }
            time.sleep(1.5)
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                cand = data["candidates"][0]["content"]["parts"][0]["text"]
                story = json.loads(cand)
                if story.get("case_name") and story.get("scenes"):
                    if not story.get("id") or story["id"] in used_ids:
                        story["id"] = f"dyn_{re.sub(r'[^a-zA-Z0-9]', '_', story['case_name']).lower()[:30]}"
                    return story
            elif res.status_code == 429:
                time.sleep(3.0)
    except Exception:
        pass
    return None


def get_next_crime_story(existing_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """Retrieves the next unique high-retention documentary story.
    Prioritizes Gemini dynamic generation across diverse categories.
    Falls back to curated iconic database cases if Gemini is unavailable.
    Guarantees 100% freshness and zero repetitive topics across all channels.
    NEVER recycles previously used cases under any circumstances.
    """
    used = load_used_story_ids()
    historical_banned = load_all_blacklisted_keywords()
    
    # Combined forbidden keywords
    all_forbidden = set(historical_banned)
    for k in (existing_keywords or []):
        clean_k = k.lower().strip()
        if len(clean_k) > 3 and clean_k not in COMMON_EXCLUDED_WORDS:
            all_forbidden.add(clean_k)
    forbidden_list = list(all_forbidden)

    # 1. Primary: Try up to 2 times to generate a brand new unique dynamic story via Gemini
    for _ in range(2):
        dynamic_story = generate_dynamic_crime_story(used, forbidden_keywords=forbidden_list)
        if dynamic_story:
            c_name = dynamic_story.get("case_name", "").lower()
            words = [w for w in re.sub(r"[^\w\s]", "", c_name).split() if len(w) > 4 and w not in COMMON_EXCLUDED_WORDS]
            if not any(w in forbidden_list for w in words):
                used.append(dynamic_story["id"])
                save_used_story_ids(used)
                return dynamic_story

    # 2. Fallback: Filter curated iconic cases, strictly excluding anything already used or scheduled
    available = []
    for c in ICONIC_TRUE_CRIME_CASES:
        cid = c["id"]
        cname = c.get("case_name", "").lower()
        if cid in used:
            continue
        # Check against forbidden entity words
        words = [w for w in re.sub(r"[^\w\s]", "", cname).split() if len(w) > 3 and w not in COMMON_EXCLUDED_WORDS]
        if any(w in forbidden_list for w in words):
            continue
        available.append(c)

    if available:
        chosen = random.choice(available)
        used.append(chosen["id"])
        save_used_story_ids(used)
        return chosen

    # 3. Emergency: If all curated cases and dynamic generation failed, raise clear error rather than recycling!
    raise RuntimeError("Khong con chu de moi nao kha dung ma chua tung dang! Tu choi dung lai de bao ve kenh khoi bi trung lap.")


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific case by its ID."""
    for c in ICONIC_TRUE_CRIME_CASES:
        if c.get("id") == case_id:
            return c
    return None
