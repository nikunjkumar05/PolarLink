"""Seed the PolarLink prototype with a realistic polar-science corpus.

Uploads through the real API so FR-06 extraction and the Module 3 search
indexes are built the same way they are for a user upload.

    python scripts/seed.py            # top up missing documents
    python scripts/seed.py --reset    # wipe the repository first
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time

import requests

DEFAULT_BASE = "http://127.0.0.1:8000"


# --------------------------------------------------------------------- PDF
def make_pdf(pages: list[list[str]]) -> bytes:
    """Minimal but valid multi-page PDF with Helvetica text."""

    def esc(text: str) -> str:
        return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    font_id = 3 + 2 * len(pages)
    page_ids = [3 + 2 * i for i in range(len(pages))]
    content_ids = [4 + 2 * i for i in range(len(pages))]

    objects: dict[int, bytes] = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: (
            f"<</Type/Pages/Kids[{' '.join(f'{i} 0 R' for i in page_ids)}]"
            f"/Count {len(pages)}>>"
        ).encode(),
        font_id: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }

    for index, lines in enumerate(pages):
        objects[page_ids[index]] = (
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Contents {content_ids[index]} 0 R"
            f"/Resources<</Font<</F1 {font_id} 0 R>>>>>>"
        ).encode()

        ops = ["BT /F1 10.5 Tf 48 752 Td"]
        for line_index, line in enumerate(lines):
            if line_index:
                ops.append("0 -13.5 Td")
            ops.append(f"({esc(line)}) Tj")
        ops.append("ET")
        stream = "\n".join(ops).encode()
        objects[content_ids[index]] = (
            f"<</Length {len(stream)}>>\nstream\n".encode() + stream + b"\nendstream"
        )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = out.tell()
        out.write(f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n")

    xref_at = out.tell()
    count = max(objects) + 1
    out.write(f"xref\n0 {count}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for number in range(1, count):
        out.write(f"{offsets[number]:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<</Size {count}/Root 1 0 R>>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    return out.getvalue()


# ---------------------------------------------------------------- corpus
def lines(paragraphs: list[str], width: int = 92) -> list[str]:
    out: list[str] = []
    for paragraph in paragraphs:
        for sentence in paragraph.replace("\n", " ").split("  "):
            current = ""
            for word in sentence.split():
                if len(current) + len(word) + 1 > width:
                    out.append(current)
                    current = word
                else:
                    current = f"{current} {word}".strip()
            if current:
                out.append(current)
        out.append("")
    while out and not out[-1]:
        out.pop()
    return out


def doc(*paragraphs: str) -> list[list[str]]:
    laid = lines(list(paragraphs))
    half = len(laid) // 2 + len(laid) % 2
    pages = [laid[:half], laid[half:]] if len(laid) > half else [laid]
    return [page for page in pages if page]


DOCUMENTS: list[dict] = [
    {
        "filename": "sea-ice-extent-maitri-2025.pdf",
        "meta": {
            "title": "Sea Ice Extent and Coastal Transect Observations, Maitri 2025",
            "description": "Daily sea ice extent readings taken along the coastal transect.",
            "asset_type": "PDF",
            "topic": "Sea Ice",
            "expedition": "IAE-42",
            "station": "Maitri",
            "year": 2025,
            "author": "NCPOR Field Cryosphere Group",
            "access_level": "PUBLIC",
            "keywords": "sea ice, extent, transect, freeze-up, Antarctic",
        },
        "body": doc(
            "Sea ice extent was measured along the coastal transect each morning between 06:00 and 08:00 local time. "
            "The transect runs 4.2 kilometres from the shoreline beacon to the offshore marker buoy and is walked in "
            "duplicate by two observers so that edge positions can be cross-checked before the record is committed.",
            "Air temperature at the shore beacon averaged minus 18 degrees Celsius through the observation window, "
            "while wind stayed below 12 knots for all but two of the twenty-one days. New fast ice formed in three "
            "distinct bands, and the outer band consolidated only after a four-day period of sustained katabatic flow.",
            "Recorded values were validated before being committed to the field log. Where a discrepancy greater than "
            "30 metres was found between observers, the transect was re-walked and both readings discarded. Two days "
            "were lost to blowing snow and are marked as gaps rather than estimated.",
            "Satellite overpass timings were logged against ground truth points so that passive microwave products "
            "could be calibrated for this stretch of coast. The comparison showed a consistent 4 to 6 kilometre "
            "overestimate of the ice edge in the standard product, attributed to the melt-pond signal along the "
            "shoreward margin.",
            "Recommendations for the next season are to move the offshore marker 300 metres further out, to record "
            "ice thickness at three points along the transect rather than one, and to carry a spare theodolite after "
            "the instrument failed on day nine.",
        ),
    },
    {
        "filename": "weddell-ice-core-albedo.pdf",
        "meta": {
            "title": "Weddell Sea Ice Core and Surface Albedo Measurements",
            "description": "Ice core stratigraphy and albedo transects from the Weddell Sea shelf.",
            "asset_type": "PDF",
            "topic": "Sea Ice",
            "expedition": "Weddell-2024",
            "station": "Halley",
            "year": 2024,
            "author": "Sea Ice Physics Team",
            "access_level": "PUBLIC",
            "keywords": "ice core, albedo, brine, snow depth, Weddell",
        },
        "body": doc(
            "Eleven ice cores were recovered from the shelf and sectioned at one centimetre intervals to resolve the "
            "brine layering produced during the winter freeze. Salinity peaked at the sample taken 40 centimetres "
            "below the surface, consistent with a refrozen meltwater lens buried under the autumn snowpack.",
            "Surface albedo was measured along a 200 metre perpendicular transect using a handheld reflectometer. "
            "Readings ranged from 0.82 over wind-packed sastrugi to 0.61 in the ponded area near the core hole, "
            "confirming that even shallow meltwater features darken the surface enough to accelerate absorption.",
            "Snow depth varied between 8 and 34 centimetres across the transect and correlated strongly with the "
            "underlying ice thickness. Deeper snow insulated the ice, leaving the growth rate lower but the spring "
            "surface brighter than the exposed ridged areas.",
            "All samples were photographed against a scale card before coring and stored at minus 25 degrees Celsius "
            "for shipboard analysis. The chain of custody form for each core is attached as an appendix to the "
            "campaign report.",
        ),
    },
    {
        "filename": "arctic-fox-survey-nyalesund.pdf",
        "meta": {
            "title": "Arctic Fox Population Survey, Ny-Alesund 2024",
            "description": "Camera-trap and den occupancy counts for the winter breeding season.",
            "asset_type": "PDF",
            "topic": "Wildlife",
            "expedition": "ArcticBio-2024",
            "station": "Ny-Alesund",
            "year": 2024,
            "author": "Terrestrial Ecology Unit",
            "access_level": "PUBLIC",
            "keywords": "arctic fox, den, camera trap, population, lemming",
        },
        "body": doc(
            "Arctic fox population notes were recorded at dawn and again at last light across fourteen known den "
            "sites. Camera traps were serviced every eleven days and the resulting images scored independently by "
            "two observers, with disagreements resolved by a third reviewer before the count was finalised.",
            "Nine of the fourteen dens showed occupancy, the highest figure recorded since monitoring began. Eight "
            "litters were confirmed with a combined total of thirty one kits, and recruitment appeared to track the "
            "preceding summer's lemming peak on the coastal plateau.",
            "Red fox incursions were logged at three coastal dens, always within two kilometres of the settlement "
            "road. No direct aggression was observed, but the affected litters were smaller, which may indicate "
            "competitive displacement rather than predation.",
            "Snow cover persisted at the inland dens more than three weeks longer than at the coastal sites, which "
            "compressed the provisioning window for the adults. Nest cameras recorded foraging trips lasting on "
            "average twelve minutes longer during that period.",
        ),
    },
    {
        "filename": "ozone-monitoring-summary-2025.pdf",
        "meta": {
            "title": "Stratospheric Ozone Monitoring Summary, 2025",
            "description": "Dobson column observations and sonde profiles for the austral spring.",
            "asset_type": "PDF",
            "topic": "Atmosphere",
            "expedition": "OzoneWatch-2025",
            "station": "Maitri",
            "year": 2025,
            "author": "Atmospheric Chemistry Group",
            "access_level": "PUBLIC",
            "keywords": "ozone, stratosphere, dobson, sonde, depletion",
        },
        "body": doc(
            "Total column ozone was measured with a Dobson spectrophotometer on every clear day of the austral "
            "spring. The seasonal minimum of 168 Dobson units was recorded on 4 October, roughly nine days earlier "
            "than the long term average for this station.",
            "Twelve ozonesonde launches provided vertical profiles through the depletion layer. The deepest loss "
            "sat between 14 and 21 kilometres, where mixing ratios fell to under 0.4 parts per million, matching "
            "the altitude range where polar stratospheric cloud formation is expected at these temperatures.",
            "Reactive chlorine derived from the sonde chemistry peaked in the same interval and declined within a "
            "week of the final warm air intrusion. The episode supports the standard activation picture rather "
            "than a local source of depletion.",
            "Brewer analyser cross checks agreed with the Dobson instrument to within two Dobson units across the "
            "campaign, and both were recalibrated after the season against the reference lamp supplied with the "
            "instrument kit.",
        ),
    },
    {
        "filename": "helheim-glacier-mass-balance.pdf",
        "meta": {
            "title": "Helheim Glacier Mass Balance and Calving Record",
            "description": "Grounded ice flux, calving flux and surface melt for the ablation season.",
            "asset_type": "PDF",
            "topic": "Glaciology",
            "expedition": "Greenland-2023",
            "station": "Kangerlussuaq",
            "year": 2023,
            "author": "Ice Dynamics Group",
            "access_level": "INTERNAL",
            "keywords": "glacier, calving, mass balance, ice flux, meltwater",
        },
        "body": doc(
            "Surface velocity at the terminus was derived from feature tracking on repeat optical imagery and "
            "checked against continuous GPS stakes installed across the shear margins. Peak flow reached 38 metres "
            "per day in late July, which is within the range observed over the previous decade.",
            "Calving flux was estimated from iceberg counts and mean berg draft, giving a season total slightly "
            "above the ten year mean. The largest single event removed a tabular block roughly 1.4 kilometres "
            "across and generated a harbour wave that was recorded by the pressure gauge on the eastern shore.",
            "Surface meltwater was routed to the ice edge through a network of moulins that opened earlier than in "
            "the two preceding seasons. Discharge at the proglacial gauge peaked in early August and then fell "
            "sharply once the accumulation zone began to refreeze at night.",
            "The net mass balance for the season was negative, driven mostly by ocean forcing at the calving front "
            "rather than by the surface melt term. Detailed processing of the radar lines is still underway and "
            "will be circulated internally before publication.",
        ),
    },
    {
        "filename": "aws-calibration-handbook.txt",
        "meta": {
            "title": "Automatic Weather Station Calibration Handbook",
            "description": "Field procedure for reconciling station telemetry with manual observations.",
            "asset_type": "OTHER",
            "topic": "Meteorology",
            "expedition": "AWS-2025",
            "station": "Dakshin Gangotri",
            "year": 2025,
            "author": "Instrumentation Cell",
            "access_level": "PUBLIC",
            "keywords": "weather station, calibration, telemetry, sensor, drift",
        },
        "body": doc(
            "Automatic weather station data was reconciled with manual readings at the start and end of every "
            "campaign. The reference instrument is a mercury thermometer and a hand held anemometer, both checked "
            "against the station master unit before the team leaves the hut.",
            "Temperature drift greater than 0.3 degrees Celsius is corrected by applying a linear offset derived "
            "from three point checks at minus twenty, zero and plus twenty degrees. Wind direction offsets are "
            "applied as a constant bearing correction measured against the survey marker.",
            "Telemetry is validated by comparing the transmitted value against the value stored on the logger card. "
            "Any mismatch larger than the sensor accuracy indicates a transmission fault rather than a sensor "
            "fault, and the card record is treated as authoritative for that interval.",
            "Sensors are cleaned before the drift check, because rime and frost on the radiation shield are the "
            "single largest source of spurious readings in winter. The cleaning step is logged separately so that "
            "data users can identify the intervals affected by icing.",
        ),
    },
    {
        "filename": "lambert-trough-sediment-dataset.csv",
        "meta": {
            "title": "Lambert Trough Sediment Core Dataset",
            "description": "Grain size, diatom assemblage and geochemistry from six trigger cores.",
            "asset_type": "DATASET",
            "topic": "Sediment",
            "expedition": "AntarcticSed-2024",
            "station": "Mawson",
            "year": 2024,
            "author": "Marine Geology Group",
            "access_level": "RESTRICTED",
            "keywords": "sediment, core, diatom, grain size, geochemistry",
        },
        "body": doc(
            "Sediment cores were recovered from the meltwater outlet channel and from three adjacent depocentres on "
            "the inner shelf. Cores were split lengthwise, photographed wet and dry, then subsampled at two "
            "centimetre intervals for grain size and for diatom counts.",
            "Grain size distributions are bimodal in the upper half of every core, with a coarse sand fraction "
            "interbedded with silty clay. The coarse bands are interpreted as ice rafted debris delivered during "
            "calving events recorded in the regional log.",
            "Diatom assemblages shift abruptly from sea ice species to open water species across the same "
            "interval, which provides an independent check on the timing of the transition. Counts were performed "
            "in triplicate and the coefficient of variation stayed below eight per cent.",
            "The dataset is held as restricted material while the trace element work is completed. Access requests "
            "are handled by the marine geology group and released only with a signed data agreement.",
        ),
    },
]


def upload(base: str, document: dict, timeout: int = 30) -> dict:
    meta = json.dumps(document["meta"])
    if document["filename"].endswith(".pdf"):
        payload = make_pdf(document["body"])
        content_type = "application/pdf"
    else:
        payload = "\n".join(
            line for page in document["body"] for line in page
        ).encode("utf-8")
        content_type = "text/plain"

    response = requests.post(
        f"{base}/api/assets",
        files={"file": (document["filename"], payload, content_type)},
        data={"meta": meta},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def wait_for(base: str, asset_id: int, timeout: float = 60.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        detail = requests.get(f"{base}/api/assets/{asset_id}", timeout=30).json()
        statuses = {version["processing_status"] for version in detail["versions"]}
        if statuses <= {"DONE", "FAILED"}:
            return detail
        time.sleep(0.4)
    raise TimeoutError(f"asset {asset_id} did not reach a terminal state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--reset", action="store_true", help="delete existing assets first")
    args = parser.parse_args()

    try:
        requests.get(f"{args.base}/api/health", timeout=10).raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"API unreachable at {args.base}: {exc}", file=sys.stderr)
        return 1

    if args.reset:
        listing = requests.get(f"{args.base}/api/assets?page_size=100", timeout=30).json()
        for item in listing["items"]:
            requests.delete(f"{args.base}/api/assets/{item['id']}", timeout=30)
        print(f"cleared {listing['total']} existing asset(s)")

    existing = {
        item["title"]
        for item in requests.get(
            f"{args.base}/api/assets?page_size=100", timeout=30
        ).json()["items"]
    }

    created = 0
    for document in DOCUMENTS:
        title = document["meta"]["title"]
        if title in existing:
            print(f"skip  {title}")
            continue
        asset = upload(args.base, document)
        detail = wait_for(args.base, asset["id"])
        created += 1
        counts = ", ".join(
            f"v{v['version_number']}={v['processing_status']}/{v['passage_count']}p"
            for v in detail["versions"]
        )
        print(f"seed  {title} [{counts}]")

    stats = requests.get(
        f"{args.base}/api/search", params={"q": "sea ice", "mode": "hybrid"}, timeout=60
    ).json()["index"]
    print(
        f"\n{created} created; index has {stats['keyword_rows']} keyword rows and "
        f"{stats['embedded_passages']}/{stats['total_passages']} passages embedded "
        f"({stats['embedding_model'] or 'no model'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
