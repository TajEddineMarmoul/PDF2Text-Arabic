"""Character-level Arabic fixes for PyMuPDF ligature decomposition.

Fixes zero-width clusters, lam-alef ligature swaps, exact-overlap pairs,
and near-overlap repositioning — all caused by PyMuPDF decomposing Arabic
ligature glyphs into visual LTR byte order.
"""

import functools
import re
import unicodedata

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


@functools.lru_cache(maxsize=256)
def is_arabic(c: str) -> bool:
    """Check if a character is Arabic (after NFKC normalization)."""
    return bool(ARABIC_RE.match(unicodedata.normalize("NFKC", c)))


def reposition(char: dict, new_x: float) -> dict:
    """Return a copy of *char* with its bbox x-coordinates set to *new_x*."""
    return {
        "c": char["c"],
        "bbox": (new_x, char["bbox"][1], new_x, char["bbox"][3]),
        "origin": char.get("origin", (0, 0)),
    }


def _reverse_cluster(cluster: list[dict], reposition_all: bool = False) -> None:
    """Reverse a ligature cluster in-place and assign decreasing x-positions.

    If *reposition_all* is False (default), the first char after reversal
    (the anchor) keeps its original bbox.  If True, every char including
    the anchor is repositioned from ``max(x0)`` downward.
    """
    cluster.reverse()
    if len(cluster) > 1:
        if reposition_all:
            anchor_x0 = max(c["bbox"][0] for c in cluster)
            for k in range(len(cluster)):
                cluster[k] = reposition(cluster[k], anchor_x0 - k * 0.01)
        else:
            ax0 = cluster[0]["bbox"][0]
            for k in range(1, len(cluster)):
                cluster[k] = reposition(cluster[k], ax0 - k * 0.01)


# ---------------------------------------------------------------------------
# Main fix pipeline
# ---------------------------------------------------------------------------


def fix_zero_width_clusters(chars: list[dict]) -> list[dict]:
    """Surgically fix zero-width and overlapping Arabic clusters.
    
    Now includes a pre-pass to de-duplicate bold rendering clones and 
    uses Unicode category checks for true diacritic merging.
    """
    if not chars:
        return chars

    # --- Phase 0: Spatial De-duplication (Remove bold clones) ---
    # Many PDFs render bold text by drawing the same char multiple times
    # with < 1.0px offsets. This pass filters them out globally for the line.
    unique_chars: list[dict] = []
    for c in chars:
        is_clone = False
        # Check against already accepted characters in this line
        for prev in unique_chars:
            if c["c"] == prev["c"]:
                b1, b2 = c["bbox"], prev["bbox"]
                # Increased threshold to 1.5px to catch wider bold offsets
                dx = abs((b1[0]+b1[2])/2 - (b2[0]+b2[2])/2)
                dy = abs((b1[1]+b1[3])/2 - (b2[1]+b2[3])/2)
                if dx < 1.5 and dy < 1.5:
                    is_clone = True
                    break
        if not is_clone:
            unique_chars.append(c)
    
    chars = unique_chars
    result: list[dict] = []
    i = 0
    while i < len(chars):
        w = chars[i]["bbox"][2] - chars[i]["bbox"][0]

        # --- Zero-width cluster ---
        # Only merge if it's a Unicode Mark (diacritic). 
        # Real letters with 0-width metadata are preserved as standalone chars.
        is_mark = unicodedata.category(chars[i]["c"][0]).startswith("M")
        if w < 0.5 and is_mark and is_arabic(chars[i]["c"]):
            cluster = [chars[i]]
            j = i + 1
            while j < len(chars):
                jw = chars[j]["bbox"][2] - chars[j]["bbox"][0]
                j_is_mark = unicodedata.category(chars[j]["c"][0]).startswith("M")
                if jw < 0.5 and j_is_mark and is_arabic(chars[j]["c"]):
                    cluster.append(chars[j])
                    j += 1
                else:
                    break
            if j < len(chars) and is_arabic(chars[j]["c"]):
                cluster.append(chars[j])
                j += 1
            _reverse_cluster(cluster)
            result.extend(cluster)
            i = j
            continue

        # --- Lam-Alef ligature ---
        if (
            w >= 0.5
            and chars[i]["c"] in "اأإآ"
            and i + 1 < len(chars)
            and chars[i + 1]["c"] == "\u0644"
        ):
            lam = chars[i + 1]
            lam_w = lam["bbox"][2] - lam["bbox"][0]
            if lam_w > w * 1.8:
                alef_bbox = chars[i]["bbox"]
                lam_bbox = lam["bbox"]

                if result and abs(result[-1]["bbox"][0] - alef_bbox[0]) < 1.0:
                    # Overlap with preceding char — place lam just after it
                    new_x = result[-1]["bbox"][0] - 0.01
                    result.append(
                        {
                            "c": "\u0644",
                            "bbox": (new_x, alef_bbox[1], new_x, alef_bbox[3]),
                            "origin": chars[i].get("origin", (0, 0)),
                        }
                    )
                    result.append(
                        {
                            "c": chars[i]["c"],
                            "bbox": lam_bbox,
                            "origin": lam.get("origin", (0, 0)),
                        }
                    )
                elif result and is_arabic(result[-1]["c"]):
                    # Word-internal/final — no swap needed (e.g. حال not حلا)
                    result.append(chars[i])
                    result.append(chars[i + 1])
                else:
                    # Word-initial/standalone — swap lam↔alef bboxes
                    result.append(
                        {
                            "c": "\u0644",
                            "bbox": alef_bbox,
                            "origin": chars[i].get("origin", (0, 0)),
                        }
                    )
                    result.append(
                        {
                            "c": chars[i]["c"],
                            "bbox": lam_bbox,
                            "origin": lam.get("origin", (0, 0)),
                        }
                    )
                i += 2
                continue

        # --- Exact-overlap ---
        if (
            w >= 0.5
            and i + 1 < len(chars)
            and is_arabic(chars[i]["c"])
            and is_arabic(chars[i + 1]["c"])
            and (chars[i + 1]["bbox"][2] - chars[i + 1]["bbox"][0]) >= 0.5
            and abs(chars[i]["bbox"][0] - chars[i + 1]["bbox"][0]) < 0.02
        ):
            cur_x1 = chars[i]["bbox"][2]
            nxt_x1 = chars[i + 1]["bbox"][2]

            if abs(cur_x1 - nxt_x1) < 0.5 or cur_x1 > nxt_x1:
                result.append(chars[i])
                if i + 2 < len(chars) and is_arabic(chars[i + 2]["c"]):
                    result.append(
                        reposition(chars[i + 1], chars[i + 2]["bbox"][0] - 0.01)
                    )
                else:
                    result.append(chars[i + 1])
                i += 2
            else:
                ref_x0 = chars[i]["bbox"][0]
                cluster = [chars[i]]
                j = i + 1
                while j < len(chars):
                    jw = chars[j]["bbox"][2] - chars[j]["bbox"][0]
                    if (
                        jw >= 0.5
                        and is_arabic(chars[j]["c"])
                        and abs(chars[j]["bbox"][0] - ref_x0) < 0.02
                    ):
                        cluster.append(chars[j])
                        j += 1
                    else:
                        break
                if j < len(chars) and is_arabic(chars[j]["c"]):
                    cluster_min_x0 = min(c["bbox"][0] for c in cluster)
                    if abs(chars[j]["bbox"][2] - cluster_min_x0) < 1.0:
                        cluster.append(chars[j])
                        j += 1
                _reverse_cluster(cluster, reposition_all=True)
                result.extend(cluster)
                i = j
            continue

        # --- Near-overlap ---
        if (
            result
            and i + 1 < len(chars)
            and is_arabic(chars[i]["c"])
            and is_arabic(chars[i + 1]["c"])
        ):
            cur_x0 = chars[i]["bbox"][0]
            candidates = []
            for k in range(len(result) - 1, max(len(result) - 4, -1), -1):
                if is_arabic(result[k]["c"]):
                    candidates.append(result[k])
                    break

            triggered = False
            for prev in candidates:
                diff = abs(prev["bbox"][0] - cur_x0)
                if 0.02 <= diff < 1.5 and abs(cur_x0 - chars[i + 1]["bbox"][2]) < 1.0:
                    result.append(reposition(chars[i], chars[i + 1]["bbox"][0] - 0.01))
                    i += 1
                    triggered = True
                    break
            if triggered:
                continue

        # Default: keep char unchanged
        result.append(chars[i])
        i += 1

    return result
