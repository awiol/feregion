"""Pinned semantic contract for the ISC Flinn-Engdahl hierarchy source."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ISC_FE_URL = "https://www.isc.ac.uk/standards/FEregions/"
DEFAULT_ISC_SOURCE = Path(".source-data/isc/fe_regions.json")
RETIRED_GEOGRAPHIC_REGIONS = frozenset({172, 299, 550})

SEISMIC_REGION_NAMES = (
    "",
    "Alaska - Aleutian Arc",
    "Southeastern Alaska to Washington",
    "Oregon, California and Nevada",
    "Baja California and Gulf of California",
    "Mexico - Guatemala Area",
    "Central America",
    "Caribbean Loop",
    "Andean South America",
    "Extreme South America",
    "Southern Antilles",
    "New Zealand Region",
    "Kermadec - Tonga - Samoa Basin Area",
    "Fiji Islands Area",
    "Vanuatu Islands",
    "Bismarck and Solomon Islands",
    "New Guinea",
    "Caroline Islands Area",
    "Guam to Japan",
    "Japan - Kuril Islands - Kamchatka Peninsula",
    "Southwestern Japan and Ryukyu Islands",
    "Taiwan Area",
    "Philippine Islands",
    "Bornea - Sulawesi",
    "Sunda Arc",
    "Myanmar and Southeast Asia",
    "India - Xizand - Sichuan - Yunnan",
    "Southern Xinjiang to Gansu",
    "Lake Issyk-Kul to Lake Baykal",
    "Western Asia",
    "Middle East - Crimea - Eastern Balkans",
    "Western Mediterranean Area",
    "Atlantic Ocean",
    "Indian Ocean",
    "Eastern North America",
    "Eastern South America",
    "Northwestern Europe",
    "Africa",
    "Australia",
    "Pacific Basin",
    "Arctic Zone",
    "Eastern Asia",
    "Northeasterb Asia, Northern Alaska to Greeland",
    "Southeastern & Antarctic Pacific Ocean",
    "Galapagos Islands Area",
    "Macquarie Loop",
    "Andaman Islands to Sumatera",
    "Baluchistan",
    "Hindu Kush and Pamir Area",
    "Northern Eurasia",
    "Antarctica",
)

# The 1995 revision keeps the original 1..729 sequence grouped into contiguous
# seismic-region ranges. Later geographical IDs 730..757 belong to earlier
# seismic regions and are recorded separately below.
_PRIMARY_RANGES = (
    (1, 1, 17),
    (2, 18, 29),
    (3, 30, 46),
    (4, 47, 52),
    (5, 53, 71),
    (6, 72, 83),
    (7, 84, 101),
    (8, 102, 142),
    (9, 143, 146),
    (10, 147, 157),
    (11, 158, 168),
    (12, 169, 179),
    (13, 180, 182),
    (14, 183, 189),
    (15, 190, 195),
    (16, 196, 208),
    (17, 209, 210),
    (18, 211, 216),
    (19, 217, 230),
    (20, 231, 241),
    (21, 242, 247),
    (22, 248, 260),
    (23, 261, 272),
    (24, 273, 293),
    (25, 294, 301),
    (26, 302, 319),
    (27, 320, 325),
    (28, 326, 334),
    (29, 335, 356),
    (30, 357, 375),
    (31, 376, 401),
    (32, 402, 414),
    (33, 415, 437),
    (34, 438, 527),
    (35, 528, 531),
    (36, 532, 549),
    (37, 550, 587),
    (38, 588, 610),
    (39, 611, 632),
    (40, 633, 655),
    (41, 656, 666),
    (42, 667, 682),
    (43, 683, 692),
    (44, 693, 699),
    (45, 700, 702),
    (46, 703, 708),
    (47, 709, 712),
    (48, 713, 720),
    (49, 721, 726),
    (50, 727, 729),
)
_EXTRA_MEMBERS = {
    5: (730,),
    7: (731,),
    10: (732,),
    25: (733, 734, 735, 736, 737),
    32: (738, 739),
    33: (740, 741, 742),
    37: (743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755),
    43: (756,),
    44: (757,),
}


def expected_regions() -> list[dict[str, object]]:
    """Return the pinned normalized seismic-region hierarchy."""

    members: dict[int, list[int]] = {number: [] for number in range(1, 51)}
    for seismic, start, end in _PRIMARY_RANGES:
        members[seismic].extend(range(start, end + 1))
    for seismic, additions in _EXTRA_MEMBERS.items():
        members[seismic].extend(additions)
    for values in members.values():
        values[:] = [number for number in values if number not in RETIRED_GEOGRAPHIC_REGIONS]
        values.sort()
    return [
        {
            "number": number,
            "name": SEISMIC_REGION_NAMES[number],
            "geographic_regions": members[number],
        }
        for number in range(1, 51)
    ]


def normalized_document() -> dict[str, object]:
    """Return the deterministic normalized ISC source document."""

    return {
        "schema_version": 1,
        "source_url": ISC_FE_URL,
        "scheme_revision": "1995",
        "seismic_regions": expected_regions(),
    }


def canonical_bytes(document: dict[str, object]) -> bytes:
    """Serialize normalized source data for semantic integrity comparison."""

    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def semantic_sha256(document: dict[str, object]) -> str:
    """Return the semantic SHA-256 of one normalized source document."""

    return hashlib.sha256(canonical_bytes(document)).hexdigest()


EXPECTED_SEMANTIC_SHA256 = "e0bb924754f2aa2d8c1c025fc3ee5e074db90cc49d7ad8cd46e26353aa12079b"
