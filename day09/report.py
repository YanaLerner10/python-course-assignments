#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Jerusalem")
UTC = ZoneInfo("UTC")

# --------- Deadlines dictionary (your request) ----------
deadlines_utc: dict[str, dt.datetime] = {
    "day01": dt.datetime(2025, 11, 1, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    # Day01 amendment exists in README; we treat day01 effective deadline as the later one:
    "day01_amendment": dt.datetime(2025, 11, 2, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day02": dt.datetime(2025, 11, 9, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day03": dt.datetime(2025, 11, 16, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day04": dt.datetime(2025, 11, 23, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day05": dt.datetime(2025, 11, 29, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day06": dt.datetime(2025, 12, 6, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day08": dt.datetime(2025, 12, 30, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day09": dt.datetime(2026, 1, 10, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "project_proposal": dt.datetime(2026, 1, 11, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "project_submission": dt.datetime(2026, 1, 25, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
}

# effective deadline for day01 = amendment if later
deadlines_utc["day01_effective"] = max(deadlines_utc["day01"], deadlines_utc["day01_amendment"])

DAY_RE = re.compile(r"\bday\s*0?(\d{1,2})\b", re.IGNORECASE)
ISO_Z_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

NAME_PATTERNS = [
    re.compile(r"\bby\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s*[-:]\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bfinal\s+project\s+proposal\s+by\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bfinal\s+project\s+proposal\s+(.+)$", re.IGNORECASE),
]

@dataclass(frozen=True)
class Issue:
    issue_id: int | None
    title: str
    created_at_utc: dt.datetime
    student_raw: str
    student_canonical: str
    assignments: tuple[str, ...]
    format_class: str

def normalize_spaces(s: str) -> str:
    return " ".join(s.strip().split())

def parse_created_at_from_fields(fields: list[str]) -> dt.datetime | None:
    # Find first ISO...Z string anywhere in the row
    for f in fields:
        m = ISO_Z_RE.search(f)
        if m:
            ts = m.group(0)
            return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
    return None

def classify_subject(title: str) -> str:
    t = normalize_spaces(title)
    tl = t.lower()
    if "final project proposal" in tl or "proposal for final project" in tl:
        if DAY_RE.search(t):
            return "combo: day + proposal"
        return "final project proposal"
    nums = DAY_RE.findall(t)
    if len(nums) >= 2:
        return "multi-day submission"
    if nums:
        if re.search(r"\bby\b", t, re.IGNORECASE):
            if re.search(r"day\s*\d{1,2}\s+by\s+", t, re.IGNORECASE):
                return "dayXX by NAME"
            return "day with 'by'"
        if re.search(r"day\s*\d{1,2}\s*[-:]\s*", t, re.IGNORECASE):
            return "dayXX - NAME"
        return "dayXX NAME (no 'by')"
    return "other"

def parse_title(title: str) -> tuple[str, tuple[str, ...]]:
    t = normalize_spaces(title)
    tl = t.lower()

    student = "UNKNOWN"
    for pat in NAME_PATTERNS:
        m = pat.search(t)
        if m:
            student = normalize_spaces(m.group(1))
            break

    assignments: list[str] = []
    for n in DAY_RE.findall(t):
        assignments.append(f"day{int(n):02d}")

    if "final project proposal" in tl or "proposal for final project" in tl:
        assignments.append("project_proposal")
    if "project submission" in tl:
        assignments.append("project_submission")

    # de-dup preserve order
    seen = set()
    uniq = []
    for a in assignments:
        if a not in seen:
            uniq.append(a)
            seen.add(a)

    return student, tuple(uniq)

def parse_students_from_readme(readme_text: str) -> list[str]:
    names = []
    for line in readme_text.splitlines():
        if line.startswith("| [") and "](" in line:
            m = re.match(r"\|\s*\[([^\]]+)\]\(", line)
            if m:
                names.append(normalize_spaces(m.group(1)))
    return names

def canonicalize_name(name: str, roster_map: dict[str, str]) -> str:
    key = normalize_spaces(name).casefold()
    return roster_map.get(key, name)

def read_subjects(subjects_path: str, roster_map: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []
    with open(subjects_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue

            fields = raw.split("\t")
            created = parse_created_at_from_fields(fields)
            if created is None:
                continue  # skip malformed rows

            # Try to get a title: usually field[2], but fall back to whole line
            title = fields[2].strip() if len(fields) >= 3 else raw.strip()

            issue_id = None
            if fields and fields[0].strip().isdigit():
                issue_id = int(fields[0].strip())

            student_raw, assignments = parse_title(title)
            student_can = canonicalize_name(student_raw, roster_map)

            issues.append(
                Issue(
                    issue_id=issue_id,
                    title=title,
                    created_at_utc=created,
                    student_raw=student_raw,
                    student_canonical=student_can,
                    assignments=assignments,
                    format_class=classify_subject(title),
                )
            )
    return issues

def human_delta(hours: float) -> str:
    sign = "-" if hours < 0 else ""
    h = abs(hours)
    days = int(h // 24)
    rem = h - 24 * days
    return f"{sign}{days}d {rem:.1f}h" if days else f"{sign}{rem:.1f}h"

def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    idx = (len(sorted_vals) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

def build_report(issues: list[Issue], roster: list[str]) -> str:
    roster_set = set(roster)

    # assignment -> student -> earliest submission time
    submissions: dict[str, dict[str, dt.datetime]] = defaultdict(dict)

    for iss in issues:
        for a in iss.assignments:
            prev = submissions[a].get(iss.student_canonical)
            if prev is None or iss.created_at_utc < prev:
                submissions[a][iss.student_canonical] = iss.created_at_utc

    # Which assignments to include
    assignments = sorted(
        set(deadlines_utc.keys()) | set(submissions.keys()),
        key=lambda a: (0, int(a[3:])) if re.fullmatch(r"day\d\d", a) else (1, a),
    )

    fmt_counts = Counter(i.format_class for i in issues)

    lines: list[str] = []
    lines.append("# Submission report\n")
    lines.append(f"Generated at (UTC): {dt.datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"Roster size: **{len(roster_set)}**\n")

    # Overview
    lines.append("## Overall coverage\n")
    lines.append("| Assignment | Deadline (Asia/Jerusalem) | Submitted | Missing | Late |")
    lines.append("|---|---|---:|---:|---:|")
    for a in assignments:
        dl = deadlines_utc.get(a)
        dl_local = "—" if dl is None else dl.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        submap = submissions.get(a, {})
        submitted = set(submap.keys())
        missing = roster_set - submitted
        late = "—"
        if dl is not None:
            late = str(sum(1 for t in submap.values() if t > dl))
        lines.append(f"| {a} | {dl_local} | {len(submitted)}/{len(roster_set)} | {len(missing)} | {late} |")
    lines.append("")

    # Subject formats
    lines.append("## Subject/title format popularity\n")
    lines.append("| Format | Count |")
    lines.append("|---|---:|")
    for fmt, c in fmt_counts.most_common():
        lines.append(f"| {fmt} | {c} |")
    lines.append("")

    # Per assignment details
    for a in assignments:
        dl = deadlines_utc.get(a)
        submap = submissions.get(a, {})
        submitted = set(submap.keys())
        missing = sorted(roster_set - submitted)

        lines.append(f"## {a}\n")
        if dl is None:
            lines.append("**Deadline:** not defined.\n")
        else:
            lines.append(f"**Deadline (Asia/Jerusalem):** {dl.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M')}  ")
            lines.append(f"**Deadline (UTC):** {dl.strftime('%Y-%m-%d %H:%M')}\n")

        lines.append(f"- **Submitted:** {len(submitted)}/{len(roster_set)}")
        lines.append(f"- **Missing:** {len(missing)}")
        if dl is not None:
            lines.append(f"- **Late:** {sum(1 for t in submap.values() if t > dl)}")
        lines.append("")

        if missing:
            lines.append("### Missing students\n")
            for s in missing:
                lines.append(f"- {s}")
            lines.append("")

        if dl is not None and submap:
            deltas = []
            late_list = []
            for student, t in submap.items():
                hours = (t - dl).total_seconds() / 3600.0
                deltas.append(hours)
                if hours > 0:
                    late_list.append((hours, student, t))
            deltas.sort()
            late_list.sort(reverse=True)

            if late_list:
                lines.append("### Late submissions (most late first)\n")
                lines.append("| Student | Submitted (Asia/Jerusalem) | Late by |")
                lines.append("|---|---|---:|")
                for hours, student, t in late_list[:20]:
                    lines.append(
                        f"| {student} | {t.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M')} | {human_delta(hours)} |"
                    )
                lines.append("")

            p10 = percentile(deltas, 0.10)
            p50 = percentile(deltas, 0.50)
            p90 = percentile(deltas, 0.90)

            lines.append("### Distribution vs deadline (hours)\n")
            lines.append(f"- **P10:** {human_delta(p10)}")
            lines.append(f"- **Median (P50):** {human_delta(p50)}")
            lines.append(f"- **P90:** {human_delta(p90)}")
            lines.append(f"- **Earliest:** {human_delta(deltas[0])}")
            lines.append(f"- **Latest:** {human_delta(deltas[-1])}\n")

    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", default="day09/subjects.txt")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--out", default="report.md")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Print a few parsed examples")
    args = parser.parse_args()

    readme_text = open(args.readme, "r", encoding="utf-8", errors="replace").read()
    roster = parse_students_from_readme(readme_text)

    if not roster:
        raise SystemExit("Could not parse roster from README.md (Students table missing?)")

    roster_map = {name.casefold(): name for name in roster}

    issues = read_subjects(args.subjects, roster_map)

    if args.debug:
        print("DEBUG roster size:", len(roster))
        print("DEBUG issues parsed:", len(issues))
        for iss in issues[:5]:
            print("TITLE:", iss.title)
            print("  student_raw:", iss.student_raw, "-> canonical:", iss.student_canonical)
            print("  assignments:", iss.assignments)
            print("  created_utc:", iss.created_at_utc, "| created_local:", iss.created_at_utc.astimezone(LOCAL_TZ))
            print()

    report = build_report(issues, roster)

    if args.stdout:
        print(report)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print("Wrote:", args.out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
