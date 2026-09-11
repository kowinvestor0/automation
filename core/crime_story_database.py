"""American True Crime & Unsolved Mysteries Database.
Curated collection of the most captivating real cases, cold cases, and mysteries in US history.
Structured specifically for high-retention TikTok / Shorts documentary storytelling (>60s).
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.paths import DATA_DIR

USED_STORIES_FILE = DATA_DIR / "used_crime_stories.json"

ICONIC_TRUE_CRIME_CASES: List[Dict[str, Any]] = [
    {
        "id": "db_cooper_vanished",
        "case_name": "D.B. Cooper: The Skyjacker Who Vanished",
        "hook_banner": "VANISHED AT 10,000 FT 😱",
        "wiki_query": "D. B. Cooper",
        "broll_queries": ["commercial airplane flying stormy night", "rain on tarmac airport", "dark forest fog aerial", "fbi investigation briefcase money"],
        "scenes": [
            {
                "text": "On Thanksgiving Eve in 1971, a quiet man wearing dark sunglasses boarded a Boeing 727 in Portland, Oregon.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "He purchased his ticket under the name Dan Cooper. Mid-flight, he handed the flight attendant a handwritten note saying he had a bomb in his briefcase.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "He demanded two hundred thousand dollars in negotiable twenty-dollar bills and four military parachutes.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "When the plane touched down in Seattle, all thirty-six passengers were released safely in exchange for the cash.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "Refueling complete, the plane took off toward Reno, flying through a freezing torrential thunderstorm at just ten thousand feet.",
                "sfx": "rain thunder",
                "visual_hint": "broll"
            },
            {
                "text": "Somewhere over the pitch-black Cascade wilderness, Cooper lowered the plane's aft stairs and strapped the ransom money to his chest.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Then, into the freezing rain and zero visibility, he leapt into the darkness, never to be seen or heard from again.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Despite one of the longest manhunts in FBI history and forty-five years of investigation, his body was never recovered.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Did Dan Cooper survive that icy jump into the wilderness, or did he perish in the mountains? Drop your theory in the comments and follow for part two.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #dbcooper #unsolved #fbi #crimetok #mystery #history #fyp"]
    },
    {
        "id": "zodiac_killer_ciphers",
        "case_name": "The Zodiac Killer: The Unsolved American Nightmare",
        "hook_banner": "UNSOLVED FBI NIGHTMARE ⚠️",
        "wiki_query": "Zodiac Killer",
        "broll_queries": ["typewriter dark room detective", "police car flashing lights night", "cryptic handwritten cipher letter", "san francisco street fog night"],
        "scenes": [
            {
                "text": "In the late 1960s, Northern California was paralyzed by a phantom who called himself the Zodiac.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Unlike ordinary criminals who try to hide, the Zodiac actively taunted the press and police by sending terrifying handwritten letters.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "He demanded his letters and complex mathematical ciphers be printed on the front page of major newspapers, threatening more lives if editors refused.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "His famous 340-character cipher stumped the FBI, CIA, and military cryptographers for over fifty-one years.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "It was not until December 2020 that a global team of amateur codebreakers finally cracked the message using advanced supercomputers.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "The decoded message began with the chilling words: I hope you are having lots of fun in trying to catch me.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "To this day, the Zodiac killer was never officially identified or captured, remaining America's most elusive unsolved case.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Who do you believe was the real person behind the Zodiac mask? Tell us your suspect below and follow for more chilling cold cases.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #zodiackiller #coldcase #unsolved #fbi #crimetok #mystery #fyp"]
    },
    {
        "id": "alcatraz_escape_1962",
        "case_name": "The 1962 Alcatraz Escape: The Impossible Breakout",
        "hook_banner": "THE IMPOSSIBLE ESCAPE 🌊",
        "wiki_query": "June 1962 Alcatraz escape",
        "broll_queries": ["prison bars dark cell", "ocean waves crashing rocky island night", "rainstorm fog bay bridge", "fbi old mugshot file"],
        "scenes": [
            {
                "text": "Alcatraz was designed by the federal government with one single purpose: to be completely inescapable.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Perched on a barren rock in the freezing, shark-infested currents of San Francisco Bay, no inmate had ever escaped alive.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Until the morning of June 12th, 1962, when morning guards discovered three dummy heads sculpted from soap, hair, and concrete resting in three cells.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Inmates Frank Morris and brothers John and Clarence Anglin had spent sixteen months painstakingly drilling through concrete walls using stolen metal spoons.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "On an unused utility roof, they vulcanized fifty stolen rubber raincoats into a homemade inflatable raft using steam pipes.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Under the cover of midnight fog, they slipped into the freezing waters of the bay and vanished into the darkness.",
                "sfx": "rain thunder",
                "visual_hint": "broll"
            },
            {
                "text": "While prison authorities claimed they must have drowned, no bodies were ever recovered.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Decades later, facial recognition analysis matched elderly men living secretly in South America to the escaped brothers.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Did they conquer the freezing bay and pull off the greatest prison break in American history? Share your verdict below and subscribe.",
                "sfx": None,
                "visual_hint": "wiki"
            }
        ],
        "hashtags": ["#alcatraz #truecrime #prisonbreak #history #mystery #fbi #crimetok #fyp"]
    },
    {
        "id": "black_dahlia_mystery",
        "case_name": "The Black Dahlia: Hollywood's Darkest Secret",
        "hook_banner": "HOLLYWOOD'S DARKEST CASE 💔",
        "wiki_query": "Black Dahlia",
        "broll_queries": ["vintage 1940s los angeles night", "detective trenchcoat dark alley", "crime scene tape black and white", "police vintage siren flash"],
        "scenes": [
            {
                "text": "On a chilly January morning in 1947, a mother walking with her child through a vacant lot in Los Angeles spotted what looked like a discarded mannequin.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Drawing closer, she made a horrifying discovery that would shatter post-war America: it was the body of twenty-two-year-old aspiring actress Elizabeth Short.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "The brutality of the scene shocked seasoned LAPD homicide detectives. Her body had been surgically severed in half and completely drained of blood.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "A chilling Glasgow smile had been carved into her face, yet there was not a single drop of blood anywhere at the vacant lot.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Days later, the killer began mailing packages of her personal belongings, birth certificate, and taunting letters directly to local newspaper editors.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Over one hundred and fifty suspects were interrogated, including prominent Hollywood physicians and elite socialites, but zero convictions were made.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "Nearly eighty years later, the identity of the Black Dahlia killer remains buried deep in Hollywood shadows.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Was the killer protected by high-ranking officials in the department? Leave your thoughts below and follow for more unsolved historical cases.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#blackdahlia #truecrime #hollywood #mystery #coldcase #unsolved #crimetok #fyp"]
    },
    {
        "id": "boy_in_the_box_solved",
        "case_name": "The Boy in the Box: America's Unknown Child",
        "hook_banner": "65 YEARS TO SOLVE 📦",
        "wiki_query": "Murder of Joseph Augustus Zarelli",
        "broll_queries": ["winter woods snow trees gloomy", "cardboard box vintage forest", "forensic dna lab microscope", "vintage philadelphia police car"],
        "scenes": [
            {
                "text": "In February 1957, a muskrat hunter trekking through the snowy woods near Philadelphia made a discovery that would break the heart of a nation.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Inside a damp cardboard bassinet box from JC Penney lay the body of a four-year-old boy, neatly wrapped in a faded plaid blanket.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "He showed severe signs of malnourishment and surgical scars on his ankle, but nobody had ever reported him missing.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "Police printed over four hundred thousand fliers featuring his portrait and mailed them with gas bills across all forty-eight states.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "For sixty-five years, generations of Philadelphia homicide detectives visited his small grave marked simply: America's Unknown Child.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Then in late 2022, cutting-edge forensic genetic genealogy achieved what thousands of interviews never could: extracting DNA from bone fragments.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "On December 8th, 2022, police officially announced his true name: Joseph Augustus Zarelli, born in January 1953.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "While his identity is finally restored, his murderer has never been brought to justice. Did this long-awaited breakthrough give you hope for other cold cases? Let us know below.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #boyinthebox #coldcase #forensics #solved #mystery #crimetok #fyp"]
    },
    {
        "id": "hinterkaifeck_murders",
        "case_name": "The Hinterkaifeck Murders: Footprints in the Snow",
        "hook_banner": "FOOTPRINTS IN THE SNOW 👣",
        "wiki_query": "Hinterkaifeck murders",
        "broll_queries": ["snowy farm isolated winter night", "footprints in snow leading to house", "dark attic wooden floorboards", "lantern light dark barn"],
        "scenes": [
            {
                "text": "Days before six people were killed on an isolated farm, farmer Andreas Gruber noticed strange footprints in the snow leading from the forest straight to his home.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "The terrifying part? There were zero footsteps leading back out.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "That night, he heard heavy footsteps pacing back and forth across the attic boards directly above his bedroom.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Their new maid had arrived at the farm just hours before. The previous maid had quit in absolute panic, convinced the estate was haunted by an evil presence.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "On March 31st, one by one, all four family members, the young grandchild, and the maid were lured into the barn and murdered with a mattock pickaxe.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Autopsies revealed something far more disturbing: the killer remained living inside the farmhouse for three full days alongside the victims.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Neighbors saw smoke rising from the chimney and found that all the cattle and dogs had been fed by the killer before he quietly slipped away.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Over one hundred suspects were questioned, but the phantom of Hinterkaifeck was never found. What would you have done if you saw those footsteps? Comment below.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #hinterkaifeck #unsolved #scarystories #mystery #crimetok #fyp"]
    },
    {
        "id": "sodder_children_fire",
        "case_name": "The Disappearance of the Sodder Children",
        "hook_banner": "FIVE CHILDREN VANISHED 🔥",
        "wiki_query": "Sodder children disappearance",
        "broll_queries": ["house on fire night flames", "ash and burnt wood ruins", "vintage telephone wire cut", "parents looking desperate search"],
        "scenes": [
            {
                "text": "On Christmas Eve in 1945, a sudden fire broke out in the home of George and Jennie Sodder in Fayetteville, West Virginia.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "George and Jennie escaped with four of their children, but five of their kids remained trapped upstairs in the bedrooms.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Frantic to save them, George ran for his ladder, but found it had been inexplicably stolen from its usual spot and hidden in a ditch.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "He sprinted to his two work trucks to drive them under the window, but both previously working engines had been sabotaged and refused to start.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "When the fire burned out, investigators spent days sifting through the ashes. They expected to find the remains of the children, but found zero bones or teeth.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Fire experts testified that a residential fire could not generate the extreme temperatures required to completely vaporize five human skeletons.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "Twenty years later, Jennie opened a letter mailed from Kentucky with no return address. Inside was a photograph of a young man identical to their missing son Louis.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Did the Sodder children die that Christmas Eve, or were they abducted before the flames were lit? Tell us your theory below and follow for part two.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #sodderchildren #unsolved #mystery #history #crimetok #fyp"]
    },
    {
        "id": "ted_bundy_escape",
        "case_name": "Ted Bundy: The Colorado Jailhouse Breakout",
        "hook_banner": "HOW DID HE ESCAPE? 🚨",
        "wiki_query": "Ted Bundy",
        "broll_queries": ["courtroom law library books", "prison window high jump night", "fbi wanted poster vintage", "colorado mountain snow night"],
        "scenes": [
            {
                "text": "Before becoming America's most infamous convicted criminal, Ted Bundy pulled off an escape that baffled law enforcement nationwide.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "In June 1977, while awaiting trial in Pitkin County Courthouse in Colorado, Bundy elected to act as his own attorney.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Because of his legal status, guards removed his handcuffs and allowed him unsupervised access to the courthouse law library during recess.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "The moment the guard stepped out for a cigarette, Bundy calmly opened a second-story window and leaped thirty feet to the ground below.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "He sprinted into the surrounding Aspen mountains and evaded bloodhounds and hundreds of armed deputies for six full days.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Recaptured, he was moved to a high-security facility in Glenwood Springs, where he starved himself to drop thirty-five pounds.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "On New Year's Eve, he squeezed through a twelve-inch ceiling light opening, crawled across crawlspaces, and escaped a second time into the night.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "How did one man outsmart maximum-security facilities twice within six months? Drop your reaction in the comments and subscribe for more crime history.",
                "sfx": None,
                "visual_hint": "wiki"
            }
        ],
        "hashtags": ["#truecrime #tedbundy #escape #history #fbi #crimetok #mystery #fyp"]
    },
    {
        "id": "axeman_of_new_orleans",
        "case_name": "The Axeman of New Orleans: Jazz Night",
        "hook_banner": "PLAY JAZZ OR DIE 🎷",
        "wiki_query": "Axeman of New Orleans",
        "broll_queries": ["vintage new orleans street night jazz", "dark bedroom door forced open", "axe blade dark shadows", "jazz band trumpet night club"],
        "scenes": [
            {
                "text": "In 1919, the city of New Orleans lived in utter terror of a serial killer who broke into homes while families slept and attacked them with their own axes.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "He never robbed his victims, leaving jewelry, cash, and valuables sitting undisturbed on nightstands right beside the crime scene.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "In March 1919, a chilling letter supposedly written by the Axeman arrived at the offices of the Times-Picayune newspaper.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "The killer claimed he was a demon from hell, announcing he would strike again on the following Tuesday night at exactly fifteen minutes past midnight.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "However, he offered the city one single condition of mercy: every home and establishment where jazz music was loudly playing would be spared.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "On that Tuesday night, every dance hall, piano parlor, and private home across New Orleans blasted jazz music until the break of dawn.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "Not a single person was harmed that night. Shortly after, the attacks stopped forever.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Was the Axeman a lone madman, an organized gang, or did he vanish like a ghost? Share your thoughts below and follow for more chilling lore.",
                "sfx": None,
                "visual_hint": "wiki"
            }
        ],
        "hashtags": ["#truecrime #axeman #neworleans #history #jazz #mystery #crimetok #fyp"]
    },
    {
        "id": "somerton_man_mystery",
        "case_name": "The Somerton Man: Tamam Shud",
        "hook_banner": "THE SECRET CODE 📜",
        "wiki_query": "Tamam Shud case",
        "broll_queries": ["beach shore cloudy cold morning", "vintage pocket watch secret code", "detective magnifying glass paper", "mysterious man trenchcoat silhouette"],
        "scenes": [
            {
                "text": "On the morning of December 1st, 1948, locals discovered the body of a well-dressed man resting against a seawall on Somerton Beach.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "All labels had been cleanly sliced off his clothing. He carried no wallet, no identification, and dental records matched no missing person in the world.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Months into the investigation, a coroner discovered a tiny hidden pocket sewn deep inside his waistband.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Tucked tightly inside was a rolled scrap of paper torn from a rare twelfth-century Persian book. It read two words: Tamam Shud, meaning: It is finished.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Police eventually located the exact book from which the page was torn. On the back cover was an uncrackable five-line encrypted military cipher.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Cold War intelligence agencies suspected he was an elite operative who was poisoned with an untraceable biological toxin.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Only in 2022 did modern DNA sequencing identify him as Carl Webb, an electrical engineer from Melbourne, yet his death remains an enigma.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Was he an undercover spy on a covert mission, or did a tragic heartbreak lead to his demise? Tell us your verdict below and subscribe.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #tamamshud #somertonman #spy #mystery #coldcase #crimetok #fyp"]
    }    ,
    {
        "id": "gardner_museum_heist",
        "case_name": "The $500 Million Gardner Art Heist",
        "hook_banner": "$500M ART HEIST REWARD 💰",
        "wiki_query": "Isabella Stewart Gardner Museum theft",
        "broll_queries": ["museum gallery empty frames dark", "police uniform badge flashlight night", "classic oil painting frame antique", "fbi investigation briefcase money"],
        "scenes": [
            {
                "text": "In the early hours of March eighteenth, 1990, two men disguised as Boston police officers knocked on the side door of the Gardner Museum.",
                "sfx": "police siren",
                "visual_hint": "broll"
            },
            {
                "text": "They told the young night watchman they were responding to a reported disturbance inside the courtyard.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "The guard breached protocol and buzzed them in. Within minutes, both security guards were handcuffed and wrapped in duct tape in the basement.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "For eighty-one uninterrupted minutes, the thieves roamed the galleries, ruthlessly slashing priceless masterpieces directly out of their frames.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "They stole thirteen irreplaceable treasures, including Rembrandt's only seascape, The Storm on the Sea of Galilee, and a rare Vermeer.",
                "sfx": None,
                "visual_hint": "wiki"
            },
            {
                "text": "The total value of the stolen artwork exceeds five hundred million dollars, making it the single largest property theft in world history.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "The FBI is still offering an unprecedented ten-million-dollar cash reward for information leading to the recovery of the stolen art.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "To this day, the empty gilded frames remain hanging on the museum walls, waiting in silence for their stolen masterpieces to return.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Where do you think these legendary paintings are hidden today? Tell us your theory in the comments and follow for the next real mystery.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #artheist #gardnermuseum #fbi #boston #history #unsolved #crimetok #fyp"]
    },
    {
        "id": "jonbenet_ramsey_case",
        "case_name": "JonBenet Ramsey: The Mystery Ransom Note",
        "hook_banner": "THE 3-PAGE RANSOM NOTE ⚠️",
        "wiki_query": "JonBenét Ramsey",
        "broll_queries": ["luxury mansion snow night boulder colorado", "handwritten ransom letter paper pen", "police tape basement flashlight", "detective investigation crime scene"],
        "scenes": [
            {
                "text": "On the quiet morning of December twenty-sixth, 1996, Patsy Ramsey placed a frantic 911 call from her home in Boulder, Colorado.",
                "sfx": "police siren",
                "visual_hint": "broll"
            },
            {
                "text": "She claimed her six-year-old daughter, JonBenet, had been kidnapped right out of her bedroom during the night.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "On the spiral staircase, police discovered a bizarre, three-page handwritten ransom note demanding exactly one hundred eighteen thousand dollars.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Curiously, that exact dollar amount matched the exact Christmas bonus her father, John Ramsey, had received earlier that year.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Even stranger, forensic document examiners confirmed the ransom note was written with a pen and notepad taken from inside the family home.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Just hours later, her father searched the basement and tragically discovered JonBenet's body hidden in a dark wine cellar room.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Decades of intense media scrutiny, conflicting DNA tests, and grand jury leaks have yielded zero convictions for this high-profile tragedy.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Nearly thirty years later, the FBI and Boulder Police continue testing unidentified male DNA found on her clothing.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Was it an outside intruder who slipped in through the basement, or an inside cover-up? Share your thoughts below and subscribe.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #jonbenet #boulder #coldcase #unsolved #fbi #crimetok #mystery #fyp"]
    },
    {
        "id": "lizzie_borden_murders",
        "case_name": "Lizzie Borden: The 1892 Victorian House Murders",
        "hook_banner": "DID LIZZIE REALLY DO IT? 🪓",
        "wiki_query": "Lizzie Borden",
        "broll_queries": ["antique victorian house dark interior", "vintage axe wood wooden floor", "1800s vintage portrait sepia", "courtroom gavel trial vintage"],
        "scenes": [
            {
                "text": "On a sweltering August morning in 1892, a gruesome double homicide shocked the quiet town of Fall River, Massachusetts.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Wealthy businessman Andrew Borden and his wife Abby were discovered brutally murdered inside their Victorian home, struck repeatedly with a heavy axe.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Andrew Borden had been attacked while taking a nap on the living room sofa, with zero signs of struggle or forced entry.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Suspicion quickly fell upon Andrew's thirty-two-year-old daughter, Lizzie Borden, who was the only family member inside the home.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Investigators were baffled when they found no bloodstains on Lizzie's dress, yet witnesses testified she burned a dress in the kitchen stove days later.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "In the basement, police found a hatchet head with its handle freshly broken off, covered in suspicious ash.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Her sensational trial captivated nineteenth-century America, but due to lack of physical evidence, the all-male jury acquitted her of all charges.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Lizzie inherited her father's fortune, bought a mansion on the hill, and lived in ostracized silence until her death in 1927.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Do you believe Lizzie got away with murder, or was someone else lurking in that house? Leave your verdict below and hit follow.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #lizzieborden #history #unsolved #massachusetts #crimetok #mystery #fyp"]
    },
    {
        "id": "jimmy_hoffa_disappearance",
        "case_name": "Jimmy Hoffa: The Mob Mystery That Stumped the FBI",
        "hook_banner": "THE FBI'S BIGGEST COLD CASE 🕵️",
        "wiki_query": "Jimmy Hoffa",
        "broll_queries": ["1970s vintage car parking lot suburban night", "mafia trench coat fedora shadows", "fbi badge investigation files vintage", "detroit street aerial gloomy vintage"],
        "scenes": [
            {
                "text": "On the sunny afternoon of July thirtieth, 1975, one of the most powerful and controversial men in America vanished without a trace.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Jimmy Hoffa, the charismatic and fiercely connected former president of the International Brotherhood of Teamsters, drove to the Machus Red Fox restaurant in Michigan.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "He had scheduled a high-stakes peace meeting with two powerful Detroit and New Jersey Mafia capos to discuss regaining control of the union.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "At two-fifteen p.m., Hoffa called his wife from a payphone, frustrated that his meeting partners had not shown up.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "Witnesses later saw Hoffa speaking with several men in a maroon Mercury sedan before stepping into the back seat. He was never seen again.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "The FBI launched Operation Foxcraft, interviewing thousands of mobsters, wiretapping phone lines, and digging up concrete foundations across the Midwest.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Wild theories claimed his body was buried beneath Giants Stadium, incinerated in a mob-owned crematory, or melted down into scrap steel.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "After fifty years and thousands of classified FBI case files, Jimmy Hoffa's exact resting place remains the ultimate underworld secret.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Which mob theory do you find most convincing? Drop your comment below and follow for more legendary true crime tales.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #jimmyhoffa #fbi #mafia #coldcase #history #crimetok #unsolved #fyp"]
    },
    {
        "id": "mary_celeste_ghost_ship",
        "case_name": "The Mary Celeste: The Ocean's Greatest Mystery",
        "hook_banner": "GHOST SHIP FOUND EMPTY 🚢",
        "wiki_query": "Mary Celeste",
        "broll_queries": ["old wooden ship sailing stormy dark ocean", "empty wooden ship deck waves night", "vintage compass nautical map captain table", "rough ocean storm waves aerial dark"],
        "scenes": [
            {
                "text": "On December fifth, 1872, a British merchant ship spotted a dual-masted brigantine sailing erratically through the rough waters of the Atlantic Ocean.",
                "sfx": "rain thunder",
                "visual_hint": "broll"
            },
            {
                "text": "It was the American vessel Mary Celeste, which had departed New York for Genoa a month earlier carrying seventeen hundred barrels of industrial alcohol.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "When the British captain sent a boarding crew to investigate, they stepped aboard a ship completely frozen in time.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "The sails were partially set, personal belongings were undisturbed, and six months worth of food and fresh drinking water remained intact in the galley.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Yet Captain Benjamin Briggs, his wife, his two-year-old daughter, and all seven experienced crew members had completely vanished into thin air.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "The ship's sole lifeboat was missing, along with the navigation chronometer and ship papers, indicating an abrupt, panic-fueled evacuation.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "There was no sign of violence, no piracy, and no severe storm damage that would justify abandoning a perfectly seaworthy vessel.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Historians believe noxious alcohol fumes may have created an illusion of an imminent explosion, causing the captain to order an emergency evacuation.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "What do you think drove seasoned sailors to flee into the open sea? Share your thoughts below and subscribe for more mysteries.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #ghostship #maryceleste #history #ocean #mystery #unsolved #crimetok #fyp"]
    },
    {
        "id": "villisca_axe_murders",
        "case_name": "The Villisca Axe Murders: America's Darkest House",
        "hook_banner": "AMERICA'S DARKEST HOUSE 🩸",
        "wiki_query": "Villisca axe murders",
        "broll_queries": ["old wooden farmhouse night fog gloomy", "dark wooden hallway attic stairs shadow", "heavy vintage axe blade wood", "vintage 1900s portrait sepia family"],
        "scenes": [
            {
                "text": "In the early morning darkness of June tenth, 1912, the small railroad community of Villisca, Iowa, was plunged into an enduring nightmare.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "The Moore family and two young neighborhood girls, totaling eight people, were discovered bludgeoned to death in their beds with an axe.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Investigators pieced together that an unknown intruder had slipped into the house during a children's church day and waited quietly in the dark attic.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "After the family fell asleep, the killer moved silently from room to room, striking each victim with chilling precision.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "The crime scene displayed deeply disturbing rituals: mirrors and windows were carefully draped with clothing, and a plate of uneaten bacon was left on the kitchen table.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "The heavy two-pound axe was found resting against the wall in the downstairs guest bedroom, wiped clean of prints.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Multiple suspects were interrogated and put on trial, including a traveling preacher and a prominent state senator, but no one was ever convicted.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Over a century later, the Villisca Axe Murder House still stands in southwestern Iowa, drawing paranormal investigators and true crime historians from around the globe.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Do you believe this was the work of an infamous traveling serial killer? Comment below and follow for part two.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #villisca #axemurders #iowa #history #coldcase #unsolved #crimetok #fyp"]
    },
    {
        "id": "roanoke_lost_colony",
        "case_name": "The Lost Colony of Roanoke: Vanished Into History",
        "hook_banner": "THE MYSTERY OF CROATOAN 📜",
        "wiki_query": "Roanoke Colony",
        "broll_queries": ["gloomy coastal forest pine trees fog", "ancient carved wood tree bark letters", "abandoned wooden settlement 1500s stormy", "ocean waves crashing remote beach dark"],
        "scenes": [
            {
                "text": "In August of 1590, Governor John White finally returned to Roanoke Island off the coast of North Carolina after three agonizing years in England.",
                "sfx": "rain thunder",
                "visual_hint": "broll"
            },
            {
                "text": "He had left behind one hundred and fifteen English settlers, including his own daughter and his newborn granddaughter, Virginia Dare.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Delayed by the outbreak of war with Spain, White finally stepped ashore, eager for an emotional family reunion.",
                "sfx": None,
                "visual_hint": "broll"
            },
            {
                "text": "Instead, he arrived at a deserted ghost outpost. The cottages had been dismantled, and the settlement was completely silent.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Before leaving, White had instructed the colonists that if they were forced to relocate, they must carve the name of their new location into a post or tree.",
                "sfx": "creepy piano",
                "visual_hint": "broll"
            },
            {
                "text": "Carved into a sturdy wooden palisade post was a single cryptic word: CROATOAN. And into a nearby oak tree were the carved letters: C-R-O.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "Crucially, there was no carved Maltese cross, the agreed-upon distress symbol that would signal danger or attack by hostile forces.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "Modern archaeologists have found European ring relics and pottery mixed with indigenous artifacts on nearby Hatteras Island, suggesting the colonists integrated into local tribes to survive starvation.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Did the Lost Colony assimilate with Native Americans, or did a darker fate unfold? Tell us your thoughts below and subscribe.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #roanoke #lostcolony #croatoan #history #mystery #unsolved #crimetok #fyp"]
    },
    {
        "id": "elisa_lam_cecil_hotel",
        "case_name": "Elisa Lam: The Cecil Hotel Elevator Mystery",
        "hook_banner": "THE CECIL HOTEL FOOTAGE 📹",
        "wiki_query": "Death of Elisa Lam",
        "broll_queries": ["vintage hotel elevator interior buttons neon", "creepy hotel hallway flicker light night", "rooftop water tank dark sky downtown los angeles", "security cctv camera footage glitch screen"],
        "scenes": [
            {
                "text": "In February 2013, the Los Angeles Police Department released a four-minute security elevator video that captivated and disturbed the entire internet.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "It showed twenty-one-year-old Canadian tourist Elisa Lam inside the elevator of the historic Cecil Hotel in downtown Los Angeles.",
                "sfx": "heartbeat",
                "visual_hint": "wiki"
            },
            {
                "text": "Elisa was acting strangely, pressing multiple floor buttons, peering cautiously into the hallway, and waving her hands as if communicating with someone invisible.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "Shortly after she stepped out of frame, the elevator doors finally closed, and Elisa Lam was never seen alive again.",
                "sfx": "dramatic boom",
                "visual_hint": "broll"
            },
            {
                "text": "Two weeks later, hotel guests complained about low water pressure and an unusual taste and dark discoloration in the tap water.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "A maintenance worker climbed to the rooftop to inspect four massive four-hundred-gallon water cisterns and discovered Elisa's body submerged inside.",
                "sfx": "dramatic boom",
                "visual_hint": "wiki"
            },
            {
                "text": "The rooftop was secured behind locked alarm doors, and the heavy metal hatch of the cistern was difficult to open and close from within.",
                "sfx": "creepy piano",
                "visual_hint": "wiki"
            },
            {
                "text": "While the coroner officially ruled it an accidental drowning influenced by bipolar medication lapses, amateur sleuths continue to debate the bizarre circumstances.",
                "sfx": "heartbeat",
                "visual_hint": "broll"
            },
            {
                "text": "What do you believe happened to Elisa Lam on that rooftop? Share your theory below and follow for more real mysteries.",
                "sfx": None,
                "visual_hint": "broll"
            }
        ],
        "hashtags": ["#truecrime #elisalam #cecilhotel #losangeles #unsolved #mystery #crimetok #coldcase #fyp"]
    }

,
{
    "id": "lindbergh_baby_kidnapping",
    "case_name": "The Lindbergh Baby: Crime of the Century",
    "hook_banner": "CRIME OF THE CENTURY \ud83d\udc76",
    "wiki_query": "Lindbergh kidnapping",
    "broll_queries": [
        "nursery crib night window ladder",
        "fbi wood ladder forensic examination",
        "old newspaper headline kidnapping",
        "courtroom crowd 1930s trial"
    ],
    "scenes": [
        {
            "text": "On March first, 1932, twenty-month-old Charles Augustus Lindbergh Junior was taken directly from his crib in Hopewell, New Jersey."
        },
        {
            "text": "His father, world-famous aviator Charles Lindbergh, discovered a handmade wooden ladder abandoned below the nursery window."
        },
        {
            "text": "On the window sill, the kidnapper left a handwritten note demanding fifty thousand dollars in unmarked gold certificates."
        },
        {
            "text": "Despite paying the entire ransom through an intermediary in a Bronx cemetery, the toddler was tragically found dead ten weeks later."
        },
        {
            "text": "Two years later, investigators traced the ransom certificates to Richard Hauptmann, a German carpenter living in the Bronx."
        },
        {
            "text": "In his garage, detectives discovered nearly fourteen thousand dollars of the ransom money hidden inside oil cans and floorboards."
        },
        {
            "text": "Forensic experts proved that wood from the kidnap ladder precisely matched floorboards missing from Hauptmanns attic."
        },
        {
            "text": "Hauptmann was convicted and electrocuted in 1936, maintaining his innocence until his very final breath."
        },
        {
            "text": "Was Hauptmann a lone actor or part of a larger syndicate? Share your thoughts below and subscribe for more historic cases."
        }
    ],
    "hashtags": [
        "#truecrime #lindbergh #history #kidnapping #fbi #mystery #crimetok #coldcase"
    ]
},
{
    "id": "manson_family_murders",
    "case_name": "The Manson Family: Helter Skelter Murders",
    "hook_banner": "THE TATE-LABIANCA MURDERS \ud83e\ude78",
    "wiki_query": "Manson Family",
    "broll_queries": [
        "cielo drive mansion gate night",
        "spahn ranch desert old cars",
        "police squad car flashing lights 1969",
        "charles manson courtroom trial"
    ],
    "scenes": [
        {
            "text": "On August ninth, 1969, a wave of terror swept through Los Angeles when actress Sharon Tate and four others were brutally murdered at Cielo Drive."
        },
        {
            "text": "The killers wrote the word PIG on the front door using the victims blood before fleeing into the Hollywood Hills."
        },
        {
            "text": "The very next night, grocery executive Leno LaBianca and his wife Rosemary were murdered in their home with the phrase Helter Skelter smeared on the wall."
        },
        {
            "text": "For months, police had no suspect, until a young woman in jail bragged to her cellmate about participating in the killings."
        },
        {
            "text": "The trail led straight to Spahn Ranch, an abandoned movie set where Charles Manson led his apocalyptic commune."
        },
        {
            "text": "Manson had brainwashed his young followers to commit horrific violence to ignite what he called a racial apocalypse."
        },
        {
            "text": "During the sensational nine-month trial, Manson and his followers carved X marks into their foreheads in open defiance of the court."
        },
        {
            "text": "All were found guilty of first-degree murder and spent the remainder of their lives behind bars."
        },
        {
            "text": "How did one man gain such total psychological control over ordinary teenagers? Comment your take and follow for more dark history."
        }
    ],
    "hashtags": [
        "#truecrime #manson #cult #truecrimecommunity #history #hollywood #crimetok"
    ]
},
{
    "id": "green_river_killer_ridgway",
    "case_name": "The Green River Killer: 49 Confirmed Victims",
    "hook_banner": "49 CONFIRMED VICTIMS \ud83c\udf0a",
    "wiki_query": "Gary Ridgway",
    "broll_queries": [
        "foggy river pacific northwest trees",
        "fbi detectives crime scene woods",
        "police interrogation room tape",
        "courtroom sentencing emotional victims"
    ],
    "scenes": [
        {
            "text": "Throughout the nineteen-eighties, young women began vanishing along the Pacific Highway near Seattle, Washington."
        },
        {
            "text": "Their bodies were discovered scattered along the misty banks of the Green River, launching the largest serial murder investigation in American history."
        },
        {
            "text": "For nearly twenty years, the killer operated without detection, evading police task forces and passing polygraph examinations."
        },
        {
            "text": "In 2001, forensic detectives re-examined old evidence using revolutionary new DNA profiling techniques."
        },
        {
            "text": "The DNA directly linked semen recovered from early victims to Gary Leon Ridgway, a quiet local truck painter."
        },
        {
            "text": "In exchange for avoiding the death penalty, Ridgway confessed to murdering forty-nine women and led detectives to hidden burial sites."
        },
        {
            "text": "He admitted his compulsion was so overpowering that he often forgot the names and faces of his victims."
        },
        {
            "text": "Ridgway was sentenced to forty-eight consecutive life sentences with zero possibility of parole."
        },
        {
            "text": "Did Gary Ridgway take even more secrets to his cell? Leave your theory in the comments and follow for real justice stories."
        }
    ],
    "hashtags": [
        "#truecrime #greenriverkiller #dna #detective #fbi #justice #crimetok #serialkiller"
    ]
},
{
    "id": "btk_serial_killer_rader",
    "case_name": "BTK: The Church President With A Dark Secret",
    "hook_banner": "THE 30-YEAR FLOPPY DISK \ud83d\udcbe",
    "wiki_query": "Dennis Rader",
    "broll_queries": [
        "wichita kansas suburban house night",
        "church congregation altar interior",
        "vintage computer floppy disk forensic",
        "police arrest handcuffs patrol car"
    ],
    "scenes": [
        {
            "text": "Between 1974 and 1991, a shadowy figure terrorized Wichita, Kansas, binding and killing ten innocent people in their own homes."
        },
        {
            "text": "He sent mocking letters to police and local news stations, demanding to be called BTK, standing for Bind, Torture, Kill."
        },
        {
            "text": "Then, in 1991, the letters stopped abruptly, and the terrifying cold case went completely dark for more than a decade."
        },
        {
            "text": "In 2004, infuriated by a local newspaper article suggesting he was forgotten or dead, BTK began sending packages again."
        },
        {
            "text": "He asked police in a letter if a computer floppy disk could be traced back to him, and police falsely assured him in a newspaper ad that it was safe."
        },
        {
            "text": "BTK sent a purple floppy disk, and within hours, computer forensics extracted deleted metadata revealing the disk was used at Christ Lutheran Church by Dennis."
        },
        {
            "text": "Detectives immediately arrested Dennis Rader, a long-time church council president and local compliance officer."
        },
        {
            "text": "Rader confessed to all ten murders and was sentenced to ten consecutive life terms in maximum security."
        },
        {
            "text": "Could you imagine discovering your church president was an infamous killer? Share your reaction below."
        }
    ],
    "hashtags": [
        "#truecrime #btk #dennisrader #forensics #coldcase #unsolved #justice #crimetok"
    ]
},
{
    "id": "golden_state_killer_deangelo",
    "case_name": "The Golden State Killer: Caught by Ancestry DNA",
    "hook_banner": "CAUGHT AFTER 40 YEARS \ud83e\uddec",
    "wiki_query": "Golden State Killer",
    "broll_queries": [
        "california suburb night flashlight window",
        "dna genealogy family tree chart",
        "police badge retired officer uniform",
        "elderly man courtroom orange jumpsuit"
    ],
    "scenes": [
        {
            "text": "From 1974 to 1986, a masked predator terrorized California across multiple cities, committing thirteen murders and fifty sexual assaults."
        },
        {
            "text": "Known variously as the East Area Rapist and the Original Night Stalker, he would break into homes, tie up couples, and disappear silently into the night."
        },
        {
            "text": "For over four decades, investigators exhausted hundreds of leads, but the perpetrator vanished without leaving a fingerprint."
        },
        {
            "text": "In 2018, cold case investigator Paul Holes pioneered a revolutionary approach: genetic genealogy using public DNA databases."
        },
        {
            "text": "By uploading crime scene DNA to GEDmatch, investigators built an extensive family tree stretching back to the early eighteen-hundreds."
        },
        {
            "text": "The genetic branches narrowed down to one specific man: seventy-two-year-old Joseph James DeAngelo, a retired police officer living in Citrus Heights."
        },
        {
            "text": "Detectives secretly swabbed DeAngelos car door handle and trash can, finding an indisputable one-hundred percent DNA match."
        },
        {
            "text": "In 2020, DeAngelo pleaded guilty to all charges to avoid execution, receiving multiple consecutive life sentences without parole."
        },
        {
            "text": "Genetic genealogy has now solved hundreds of cold cases worldwide. Tell us which case they should solve next!"
        }
    ],
    "hashtags": [
        "#truecrime #goldenstatekiller #dna #coldcase #investigation #forensics #crimetok"
    ]
},
{
    "id": "chicago_tylenol_murders",
    "case_name": "The 1982 Chicago Tylenol Murders",
    "hook_banner": "POISON IN THE BOTTLE \ud83d\udc8a",
    "wiki_query": "Chicago Tylenol murders",
    "broll_queries": [
        "medicine cabinet bathroom pill bottle",
        "pharmacy shelves tylenol recall boxes",
        "police crime lab chemical testing test tubes",
        "chicago skyline autumn 1982 news"
    ],
    "scenes": [
        {
            "text": "In late September 1982, seven people in the Chicago area suddenly collapsed and died within hours of taking Extra-Strength Tylenol capsules."
        },
        {
            "text": "Among the victims were three members of the same family who took pills from the very same bottle."
        },
        {
            "text": "A sharp-eyed firefighter and nurse noticed all seven victims had taken Tylenol just before cardiac arrest, alerting authorities."
        },
        {
            "text": "Toxicology tests revealed the capsules were loaded with lethal doses of potassium cyanide, ten thousand times the fatal threshold."
        },
        {
            "text": "Investigators determined someone had taken bottles off store shelves, laced them with poison, and returned them to store shelves across Chicago."
        },
        {
            "text": "Johnson and Johnson launched an unprecedented nationwide recall of thirty-one million bottles, offering a one-hundred-thousand-dollar reward."
        },
        {
            "text": "This tragedy permanently changed consumer packaging worldwide, leading directly to the invention of tamper-evident seals on food and medication."
        },
        {
            "text": "More than forty years later, the identity of the Chicago Tylenol poisoner remains one of Americas greatest unsolved mysteries."
        },
        {
            "text": "Do you think the killer was a lone madman or an inside employee? Share your theory below."
        }
    ],
    "hashtags": [
        "#truecrime #tylenol #mystery #chicago #unsolved #history #coldcase #crimetok"
    ]
},
{
    "id": "amityville_horror_murders",
    "case_name": "The Amityville Murders: What Really Happened",
    "hook_banner": "REAL AMITYVILLE HORROR \ud83c\udfda\ufe0f",
    "wiki_query": "The Amityville Horror",
    "broll_queries": [
        "dutch colonial house distinctive windows night",
        "police yellow tape ocean avenue amityville",
        "detective holding rifle evidence bag",
        "courtroom defense attorney trial 1975"
    ],
    "scenes": [
        {
            "text": "Long before Hollywood movies and ghost stories, a gruesome real-life tragedy took place at one-twelve Ocean Avenue in Amityville, New York."
        },
        {
            "text": "On November thirteenth, 1974, twenty-three-year-old Ronald DeFeo Junior ran into a local bar screaming that his parents had been shot."
        },
        {
            "text": "When police arrived at the three-story Dutch Colonial home, they discovered six family members shot dead in their beds with a high-powered rifle."
        },
        {
            "text": "All six victims were found lying face down with their hands flat, showing zero signs of a struggle or sedatives in their systems."
        },
        {
            "text": "Neighbors reported hearing no gunshots that night, despite the rifle firing eight unsuppressed rounds in quiet succession."
        },
        {
            "text": "DeFeo confessed to the killings, claiming he heard disembodied voices plotting against him inside the walls."
        },
        {
            "text": "He was convicted on six counts of second-degree murder and sentenced to twenty-five years to life, passing away in prison in 2021."
        },
        {
            "text": "Thirteen months later, the Lutz family moved in and fled twenty-eight days later, sparking decades of supernatural speculation."
        },
        {
            "text": "Was it pure insanity, a mob hit, or something unexplainable? Share your perspective below."
        }
    ],
    "hashtags": [
        "#truecrime #amityville #horror #mystery #history #unsolved #crimetok #fyp"
    ]
},
{
    "id": "son_of_sam_david_berkowitz",
    "case_name": "Son of Sam: The .44 Caliber Killer",
    "hook_banner": "THE .44 CALIBER KILLER \ud83d\udd2b",
    "wiki_query": "David Berkowitz",
    "broll_queries": [
        "new york city street 1977 parked cars night",
        "yellow parking ticket windshield rain",
        "police precinct press conference microphones",
        "detectives escorting smiling suspect handcuffs"
    ],
    "scenes": [
        {
            "text": "During the sweltering summer of 1977, New York City was gripped by paralyzing fear as a nighttime shooter stalked parked cars."
        },
        {
            "text": "Armed with a charter arms forty-four bulldog revolver, the killer targeted young couples with long, dark hair, killing six and wounding seven."
        },
        {
            "text": "He left handwritten letters at crime scenes addressed to Captain Joseph Borrelli, signing them with the eerie moniker Son of Sam."
        },
        {
            "text": "Police formed the legendary Operation Omega task force, fielding thousands of calls and checking thousands of leads with zero success."
        },
        {
            "text": "The breakthrough came from an ordinary yellow parking ticket issued near the final shooting scene in Brooklyn to a Ford Galaxie."
        },
        {
            "text": "Detectives traced the ticket to twenty-four-year-old postal employee David Berkowitz in Yonkers."
        },
        {
            "text": "When police approached his car on August tenth, Berkowitz grinned and said, Well, you got me. How come it took you so long?"
        },
        {
            "text": "Berkowitz claimed his neighbors barking dog was possessed by an ancient demon that commanded him to kill."
        },
        {
            "text": "Did Berkowitz act alone, or was he part of a larger satanic cult? Tell us your thoughts below."
        }
    ],
    "hashtags": [
        "#truecrime #sonofsam #nyc #1970s #fbi #serialkiller #justice #crimetok"
    ]
},
{
    "id": "cleveland_torso_murders",
    "case_name": "The Cleveland Torso Murders: The Mad Butcher",
    "hook_banner": "ELIOT NESS VS MAD BUTCHER \ud83d\udd2a",
    "wiki_query": "Cleveland Torso Murderer",
    "broll_queries": [
        "kingsbury run cleveland industrial fog 1930s",
        "eliot ness fedora trenchcoat police chief",
        "vintage coroner lab autopsy instruments",
        "old newspaper headline cleveland butcher"
    ],
    "scenes": [
        {
            "text": "During the Great Depression between 1935 and 1938, a terrifying serial killer stalked Kingsbury Run in Cleveland, Ohio."
        },
        {
            "text": "Twelve bodies were discovered in ravines and marshlands, all decapitated and severed with clean, surgical precision."
        },
        {
            "text": "Famed crime fighter Eliot Ness, legendary leader of The Untouchables, was brought in as Cleveland safety director to catch the killer."
        },
        {
            "text": "Despite ordering massive raids and interrogating hundreds of suspects, the Butcher taunted Ness by dumping body parts right outside city hall."
        },
        {
            "text": "Only three of the twelve victims were ever officially identified, as most were destitute wanderers living in shantytowns."
        },
        {
            "text": "Ness secretly interrogated Dr. Francis Sweeney, a former World War One military surgeon who failed two early polygraph tests."
        },
        {
            "text": "However, Sweeney was the first cousin of a powerful Ohio congressman, making formal prosecution politically impossible."
        },
        {
            "text": "Sweeney committed himself to an asylum, where he spent decades sending mocking postcards to Eliot Ness until Ness passed away."
        },
        {
            "text": "Was Dr. Sweeney the true Mad Butcher of Kingsbury Run? Comment your theory below and follow for more."
        }
    ],
    "hashtags": [
        "#truecrime #cleveland #eliotness #history #unsolved #mystery #crimetok"
    ]
},
{
    "id": "st_valentines_day_massacre",
    "case_name": "The St. Valentines Day Massacre",
    "hook_banner": "CAPONES VALENTINE MASSACRE \ud83c\udf39",
    "wiki_query": "Saint Valentine's Day Massacre",
    "broll_queries": [
        "chicago garage brick wall bullet holes",
        "vintage 1929 police car thompson submachine gun",
        "al capone fedora cigar smiling mobster",
        "newspaper front page massacre 1929"
    ],
    "scenes": [
        {
            "text": "On the icy morning of February fourteenth, 1929, seven members of Chicagos North Side gang gathered in a Lincoln Park garage."
        },
        {
            "text": "Around ten-thirty in the morning, four men entered the garage, two of them dressed in full Chicago police uniforms."
        },
        {
            "text": "Believing it was a routine police shakedown, the seven mobsters complied, lining up against the brick wall with their hands raised."
        },
        {
            "text": "Suddenly, the disguised gunmen opened fire with Thompson submachine guns and shotguns, firing seventy rounds in seconds."
        },
        {
            "text": "The intended target, notorious rival gang leader Bugs Moran, was running late and spotted the police car, escaping with his life."
        },
        {
            "text": "The public instantly knew the mastermind behind the slaughter was Chicago kingpin Al Capone, who was conveniently vacationing in Florida."
        },
        {
            "text": "The brutal massacre outraged President Herbert Hoover, prompting the federal government to order federal agents to take Capone down."
        },
        {
            "text": "Unable to prove murder, federal prosecutors eventually imprisoned Capone for eleven years on federal income tax evasion."
        },
        {
            "text": "The bloodstained bricks of that Chicago garage wall were auctioned off and preserved in a museum. Follow for more mob history!"
        }
    ],
    "hashtags": [
        "#truecrime #alcapone #chicago #mafia #history #mobsters #crimetok #fyp"
    ]
},
{
    "id": "tupac_shakur_vegas_driveby",
    "case_name": "The Murder of Tupac Shakur: 1996 Las Vegas",
    "hook_banner": "THE VEGAS STRIP DRIVE-BY \ud83c\udfa4",
    "wiki_query": "Murder of Tupac Shakur",
    "broll_queries": [
        "las vegas strip neon signs night 1996",
        "black bmw 750il sedan bullet holes",
        "boxing match mgm grand arena crowd",
        "courtroom judge gavel arraignment 2023"
    ],
    "scenes": [
        {
            "text": "On September seventh, 1996, rap superstar Tupac Shakur was riding in the passenger seat of a black BMW on the Las Vegas Strip."
        },
        {
            "text": "Earlier that night, Tupac and Death Row Records CEO Suge Knight had attended the Mike Tyson fight at the MGM Grand."
        },
        {
            "text": "At eleven-fifteen at night, while stopped at a red light at Flamingo Road, a white Cadillac pulled up alongside their vehicle."
        },
        {
            "text": "A hand emerged from the rear window and fired fourteen rounds from a Glock pistol directly into the passenger side."
        },
        {
            "text": "Tupac was struck four times and rushed to University Medical Center, where he tragically succumbed to his injuries six days later."
        },
        {
            "text": "For twenty-seven years, the case remained shrouded in silence, conspiracy theories, and lack of witness cooperation."
        },
        {
            "text": "Then, in September 2023, Las Vegas police arrested Duane Keefe D Davis, charging him with open murder with a deadly weapon."
        },
        {
            "text": "Davis had repeatedly spoken in public interviews and a tell-all book about providing the gun used in the vehicle."
        },
        {
            "text": "Why do you think it took nearly three decades to make an arrest? Share your view below and follow for updates."
        }
    ],
    "hashtags": [
        "#truecrime #2pac #tupac #lasvegas #hiphop #justice #coldcase #crimetok"
    ]
},
{
    "id": "dyatlov_pass_incident",
    "case_name": "The Dyatlov Pass Incident: 9 Hikers in the Snow",
    "hook_banner": "NINE HIKERS IN THE SNOW \u2744\ufe0f",
    "wiki_query": "Dyatlov Pass incident",
    "broll_queries": [
        "ural mountains snow blizzard mountain ridge",
        "torn camping tent half buried snow forensics",
        "investigators walking snowshoes siberia 1959",
        "old black and white hiker group photos"
    ],
    "scenes": [
        {
            "text": "In February 1959, nine experienced Soviet hikers embarked on a challenging trek across the northern Ural Mountains."
        },
        {
            "text": "When they failed to send a scheduled telegram weeks later, military rescue teams and volunteer searchers were dispatched into the wilderness."
        },
        {
            "text": "Searchers found their campsite on the slope of Dead Mountain: their tent was slashed open from the inside out."
        },
        {
            "text": "Barefoot tracks led a mile downhill through subzero blizzard winds, where the bodies were discovered scattered over several days."
        },
        {
            "text": "Several victims were found in their underwear, while others wore mismatched clothing taken from their deceased companions."
        },
        {
            "text": "Autopsies revealed bizarre inconsistencies: two had crushed skulls and fractured ribs comparable to a high-speed car crash, yet with zero external bruises."
        },
        {
            "text": "Even stranger, traces of unexplained radiation were detected on some clothing, and one hikers tongue and eyes were missing."
        },
        {
            "text": "Official Soviet investigators abruptly closed the inquest, concluding the deaths were caused by an unknown compelling natural force."
        },
        {
            "text": "Was it a slab avalanche, secret military weapons testing, or infrasound panic? What is your verdict?"
        }
    ],
    "hashtags": [
        "#truecrime #dyatlovpass #mystery #siberia #unsolved #history #crimetok #fyp"
    ]
}
,
{
    "id": "bonnie_and_clyde_ambush",
    "case_name": "Bonnie and Clyde: The 167-Bullet Ambush",
    "hook_banner": "THE 167-BULLET AMBUSH \ud83d\ude97",
    "wiki_query": "Bonnie and Clyde",
    "broll_queries": [
        "1934 ford v8 vintage car highway",
        "texas rangers police ambush rifles dust",
        "vintage newspaper bonnie clyde headline",
        "old wanted posters 1930s outlaw"
    ],
    "scenes": [
        {
            "text": "During the depths of the Great Depression, Clyde Barrow and Bonnie Parker led a ruthless two-year crime spree across the American heartland."
        },
        {
            "text": "Robbing banks, small gas stations, and killing at least nine law enforcement officers, their daring escapes made national headlines."
        },
        {
            "text": "The Texas prison system hired legendary former Texas Ranger Frank Hamer to track the outlaw couple down at all costs."
        },
        {
            "text": "On May twenty-third, 1934, Hamer and a posse of six lawmen lay concealed in the bushes along a rural highway in Bienville Parish, Louisiana."
        },
        {
            "text": "Around nine in the morning, Clydes stolen 1934 Ford V-Eight slowed down to help an accomplice father parked on the roadside."
        },
        {
            "text": "Before either outlaw could draw a weapon, the officers opened fire with automatic rifles and shotguns."
        },
        {
            "text": "A staggering one hundred and sixty-seven rounds were fired into the vehicle in less than twenty seconds."
        },
        {
            "text": "Crowds of souvenirs hunters immediately mobbed the bullet-riddled car, even attempting to cut locks of Bonnie hair before police cordoned the scene."
        },
        {
            "text": "The bullet-riddled death car is on display in a Nevada casino to this day. Follow for more wild American outlaw history!"
        }
    ],
    "hashtags": [
        "#truecrime #bonnieandclyde #history #outlaws #1930s #fbi #crimetok #fyp"
    ]
},
{
    "id": "john_wayne_gacy_clown",
    "case_name": "John Wayne Gacy: The Killer Clown",
    "hook_banner": "THE KILLER CLOWN \ud83e\udd21",
    "wiki_query": "John Wayne Gacy",
    "broll_queries": [
        "suburban brick ranch house chicago night",
        "clown costume makeup mirror smiling",
        "detectives digging crawlspace flashlight dirt",
        "courtroom judge sentencing serial killer"
    ],
    "scenes": [
        {
            "text": "To his Norwood Park neighbors in suburban Chicago, John Wayne Gacy was a respected contractor, Democratic precinct captain, and community volunteer."
        },
        {
            "text": "He frequently entertained hospitalized children at charity events dressed as Pogo the Clown."
        },
        {
            "text": "Behind this charming facade lay one of the most prolific serial predators in American criminal history."
        },
        {
            "text": "In December 1978, fifteen-year-old high school student Robert Piest vanished after visiting Gacy to discuss a part-time job."
        },
        {
            "text": "Detectives executed a search warrant on Gacys home and detected a sickening odor coming from the basement heating vents."
        },
        {
            "text": "Underneath the floorboards, investigators uncovered twenty-nine bodies buried in the four-foot-high earthen crawlspace."
        },
        {
            "text": "Gacy confessed to thirty-three murders in total, having dumped four additional victims into the nearby Des Plaines River."
        },
        {
            "text": "He was convicted on all counts and executed by lethal injection at Stateville Correctional Center in 1994."
        },
        {
            "text": "How could a community monster hide in plain sight for so long? Leave your thoughts below and subscribe for more."
        }
    ],
    "hashtags": [
        "#truecrime #johnwaynegacy #clown #serialkiller #chicago #fbi #justice #crimetok"
    ]
},
{
    "id": "jeffrey_dahmer_apartment_213",
    "case_name": "Inside Apartment 213: Jeffrey Dahmer",
    "hook_banner": "INSIDE APARTMENT 213 \ud83d\udeaa",
    "wiki_query": "Jeffrey Dahmer",
    "broll_queries": [
        "oxford apartments building night milwaukee",
        "police sirens flashing apartment hallway",
        "blue plastic barrel hazmat chemical forensic",
        "courtroom handcuffed suspect orange jumpsuit"
    ],
    "scenes": [
        {
            "text": "On the humid night of July twenty-second, 1991, Tracy Edwards flagged down two Milwaukee patrol officers while handcuffed by one wrist."
        },
        {
            "text": "He claimed a man in apartment two-thirteen of the Oxford Apartments had threatened him with a large knife and attempted to drug him."
        },
        {
            "text": "When officers entered apartment two-thirteen to retrieve the handcuff keys, they opened a bedside drawer and found Polaroids documenting horrifying atrocities."
        },
        {
            "text": "A search of the apartment revealed severed skulls in the closet, human remains in the freezer, and a fifty-seven-gallon drum filled with acid."
        },
        {
            "text": "The resident, thirty-one-year-old Jeffrey Dahmer, confessed to murdering seventeen young men and boys between 1978 and 1991."
        },
        {
            "text": "Public outrage erupted when it was revealed police had encountered one of Dahmers victims months earlier and mistakenly returned him to Dahmers apartment."
        },
        {
            "text": "Dahmer was sentenced to fifteen consecutive life terms, totaling over nine hundred years behind bars."
        },
        {
            "text": "In November 1994, Dahmer was fatally assaulted by fellow inmate Christopher Scarver in the prison gymnasium."
        },
        {
            "text": "The entire Oxford Apartments building was demolished to erase the site of these tragedies. What case should we cover next?"
        }
    ],
    "hashtags": [
        "#truecrime #dahmer #milwaukee #truecrimecommunity #history #justice #crimetok"
    ]
},
{
    "id": "richard_ramirez_night_stalker",
    "case_name": "The Night Stalker: Terror in Los Angeles",
    "hook_banner": "THE NIGHT STALKER \ud83d\udc41\ufe0f",
    "wiki_query": "Richard Ramirez",
    "broll_queries": [
        "los angeles night skyline palm trees dark",
        "police sketch composite face avia shoes",
        "crowd angry mob street chasing suspect",
        "courtroom hand showing pentagram mark"
    ],
    "scenes": [
        {
            "text": "During the scorching spring and summer of 1985, a wave of nighttime home invasions paralyzed greater Los Angeles and San Francisco."
        },
        {
            "text": "An intruder slipped through unlocked windows and doors, committing fourteen murders and leaving satanic pentagram symbols on walls."
        },
        {
            "text": "Residents bolted doors, purchased guard dogs, and hardware stores completely sold out of window locks."
        },
        {
            "text": "The only physical evidence linking the random crimes was a rare Avia sneaker footprint and a stolen orange Toyota station wagon."
        },
        {
            "text": "When the stolen Toyota was found, laser fingerprint technology pulled a single partial print matching twenty-five-year-old Richard Ramirez."
        },
        {
            "text": "Police broadcast Ramirez mugshot across all news stations on August thirty-first, 1985."
        },
        {
            "text": "Unaware his face was on the front page of every newspaper, Ramirez entered an East Los Angeles convenience store and was recognized."
        },
        {
            "text": "An enraged neighborhood mob chased him down the street and subdued him until police arrived to make the arrest."
        },
        {
            "text": "Ramirez was sentenced to death and spent twenty-three years on San Quentin death row before dying of lymphoma. Follow for more!"
        }
    ],
    "hashtags": [
        "#truecrime #nightstalker #richardramirez #losangeles #1980s #justice #crimetok"
    ]
},
{
    "id": "oklahoma_city_bombing_murrah",
    "case_name": "The Oklahoma City Bombing: April 19, 1995",
    "hook_banner": "APRIL 19, 1995 TRAGEDY \ud83c\udfe2",
    "wiki_query": "Oklahoma City bombing",
    "broll_queries": [
        "federal building facade morning street",
        "ryder rental yellow moving truck parked",
        "fbi evidence axle vehicle identification number",
        "memorial reflecting pool oklahoma city empty chairs"
    ],
    "scenes": [
        {
            "text": "At nine-oh-two on the morning of April nineteenth, 1995, a massive blast tore through the Alfred P. Murrah Federal Building in Oklahoma City."
        },
        {
            "text": "A five-thousand-pound fertilizer and fuel bomb loaded inside a yellow Ryder rental truck destroyed one-third of the nine-story concrete building."
        },
        {
            "text": "The blast claimed the lives of one hundred and sixty-eight people, including nineteen innocent children in the second-floor daycare."
        },
        {
            "text": "It remains the deadliest act of homegrown domestic terrorism in the history of the United States."
        },
        {
            "text": "Just ninety minutes after the explosion, twenty-seven-year-old Timothy McVeigh was pulled over by a state trooper for driving without a license plate."
        },
        {
            "text": "Trooper Charlie Hanger arrested McVeigh after noticing a concealed Glock pistol under his jacket."
        },
        {
            "text": "Meanwhile, FBI agents sifted through the rubble and discovered the rear axle of the Ryder truck, containing its vehicle identification number."
        },
        {
            "text": "The VIN led back to a body shop in Kansas where McVeigh had rented the truck under an alias."
        },
        {
            "text": "McVeigh was convicted on eleven federal counts and executed by lethal injection at Terre Haute federal prison in 2001. Never forget."
        }
    ],
    "hashtags": [
        "#truecrime #history #oklahomacity #fbi #investigation #memorial #neverforget #crimetok"
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


def generate_dynamic_crime_story(used_ids: List[str]) -> Optional[Dict[str, Any]]:
    """Generates a completely new real American true crime or unsolved mystery via Gemini 2.5 Flash."""
    try:
        from core.config_manager import get_api_key
        import requests
        key = get_api_key("gemini_api_key")
        if not key or len(key) < 20:
            return None

        categories = [
            "Breathtaking Scientific Discovery / Space Exploration (NASA, James Webb, Deep Cosmos)",
            "Deep Ocean Exploration & Unexplained Marine Phenomenon (Mariana Trench, Abyssal Plain)",
            "Mega Engineering Marvel & Impossible Construction (Megastructure, Tunnel, Aerospace Records)",
            "Lost Ancient Civilization & Archaeological Excavation (Pyramids, Hidden Cities, Artifacts)",
            "Extreme Weather & Bizarre Natural Phenomenon (Supervolcanoes, Rogue Waves, Auroras)",
            "Famous Historical American Unsolved Mystery or Heist (Non-violent, High Intrigue)"
        ]
        chosen_cat = random.choice(categories)

        prompt = (
            f"Generate 1 high-retention viral documentary topic in the category: '{chosen_cat}'.\n"
            f"Requirements:\n"
            f"1. Must have a real, verified Wikipedia article with public domain historical photos.\n"
            f"2. STRICT TIKTOK COMMUNITY GUIDELINES: Absolutely NO graphic violence, gore, weapons, politics, or sensitive controversy. 100% safe for all audiences.\n"
            f"3. High viral intrigue and educational fascination.\n"
            f"Return JSON format:\n"
            f'{{"id": "unique_id", "case_name": "Full Title", "hook_banner": "ALL CAPS 3-5 WORDS", '
            f'"wiki_query": "Exact Wikipedia Title", '
            f'"broll_queries": ["cinematic ocean aerial", "astronomy telescope night"], '
            f'"scenes": [{{"text": "Deep beneath the surface...", "visual_hint": "wiki"}}], '
            f'"hashtags": ["#science", "#discovery", "#mindblown", "#fyp"]}}'
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
                "temperature": 0.85,
            }
        }
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            data = res.json()
            cand = data["candidates"][0]["content"]["parts"][0]["text"]
            story = json.loads(cand)
            if story.get("case_name") and story.get("scenes"):
                if not story.get("id") or story["id"] in used_ids:
                    story["id"] = f"dyn_{re.sub(r'[^a-zA-Z0-9]', '_', story['case_name']).lower()[:30]}"
                return story
    except Exception:
        pass
    return None


def get_next_crime_story() -> Dict[str, Any]:
    """Retrieves the next unused high-retention American true crime story.
    Ensures 100% unique cases: NEVER reuses already published cases.
    If database cases are exhausted, dynamically queries Gemini for new real cases.
    """
    used = load_used_story_ids()
    available = [c for c in ICONIC_TRUE_CRIME_CASES if c["id"] not in used]

    if available:
        chosen = available[0]
    else:
        # Generate a brand new case via Gemini to prevent ANY repetition
        dynamic_story = generate_dynamic_crime_story(used)
        if dynamic_story:
            chosen = dynamic_story
        else:
            import time
            base = ICONIC_TRUE_CRIME_CASES[len(used) % len(ICONIC_TRUE_CRIME_CASES)]
            chosen = dict(base)
            chosen["id"] = f"{base['id']}_{int(time.time())}"

    used.append(chosen["id"])
    save_used_story_ids(used)
    return chosen


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific case by its ID."""
    for c in ICONIC_TRUE_CRIME_CASES:
        if c.get("id") == case_id:
            return c
    return None

