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


def get_next_crime_story() -> Dict[str, Any]:
    """Retrieves the next unused high-retention American true crime story.
    Cycles seamlessly and ensures continuous infinite production without repeats.
    """
    used = load_used_story_ids()
    available = [c for c in ICONIC_TRUE_CRIME_CASES if c["id"] not in used]

    if not available:
        # If all cases used, reset cycle so continuous production keeps running smoothly
        used = []
        save_used_story_ids([])
        available = list(ICONIC_TRUE_CRIME_CASES)

    chosen = available[0]
    used.append(chosen["id"])
    save_used_story_ids(used)
    return chosen


def get_case_by_id(case_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific case by its ID."""
    for c in ICONIC_TRUE_CRIME_CASES:
        if c.get("id") == case_id:
            return c
    return None

