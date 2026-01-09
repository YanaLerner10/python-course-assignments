#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo

# -------------------------
# 1) HARD-CODED DEADLINES
# -------------------------
LOCAL_TZ = ZoneInfo("Asia/Jerusalem")
UTC = ZoneInfo("UTC")

deadlines = {
    "day01": dt.datetime(2025, 11, 1, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day01_amendment": dt.datetime(2025, 11, 2, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day02": dt.datetime(2025, 11, 9, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day06": dt.datetime(2025, 12, 6, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day08": dt.datetime(2025, 12, 30, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "day09": dt.datetime(2026, 1, 10, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "project_proposal": dt.datetime(2026, 1, 11, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
    "project_submission": dt.datetime(2026, 1, 25, 22, 0, tzinfo=LOCAL_TZ).astimezone(UTC),
}

# -------------------------
# 2) PARSING RULES
# -------------------------
DAY_RE = re.compile(r"\bday\s*0?(\d{1,2})\b", re.IGNORECASE)

NAME_PATTERNS = [
    re.compile(r"\bby\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s*[-:]\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s+(.+)$", re.IGNORECASE),
    re.compile(r"proposal\s+for\s+final\s+project[-:]\s*(.+)$", re.IGNORECASE),
]

PROJECT_PATTERNS = [
    # try to catch project-related subjects, in case people used them
    re.compile(r"\bfinal\s+project\s+proposal\b", re.IGNORECASE),
    re.compile(r"\bproject\s+proposal\b", re.IGNORECASE),
    re.compile(r"\bproject\s+submission\b", re.IGNORECASE),
]

@dataclass(frozen=True)
class Issue:
    issue_id: int
    state: str
    title: str
    created_at_utc: dt.datetime
    student: str
    assignments: tuple[str, ...]
    format_class: str


def normalize_spaces(s: str) -> str:
    return " ".join(s.strip().split())


def parse_issue_created_at(s: str) -> dt.datetime:
    # Example: 2026-01-03T18:44:38Z
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s).astimezone(UTC)


def classify_title_format(title: str) -> str:
    t = normalize_spaces(title)
    tl = t.lower()

    # project proposal style
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

    # student name
    student = None
    for pat in NAME_PATTERNS:
        m = pat.search(t)
        if m:
            student = normalize_spaces(m.group(1))
            break
    if student is None:
        student = "UNKNOWN"

    assignments: list[str] = []

    # dayXX detection
    for n in DAY_RE.findall(t):
        assignments.append(f"day{int(n):02d}")

    # project detection (best-effort, optional)
    if "final project proposal" in tl or "proposal for final project" in tl:
        assignments.append("project_proposal")
    elif "project submission" in tl:
        assignments.append("project_submission")

    # de-dup preserve order
    seen = set()
    out: list[str] = []
    for a in assignments:
        if a not in seen:
            out.append(a)
            seen.add(a)

    return student, tuple(out)


def read_subjects(subjects_path: str) -> list[Issue]:
    issues: list[Issue] = []
    with open(subjects_path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw.strip():
                continue
            parts = raw.split("\t")
            if len(parts) < 4:
                continue

            issue_id = int(parts[0])
            state = parts[1].strip()
            title = parts[2].strip()
            created = parts[-1].strip()

            created_at_utc = parse_issue_created_at(created)
            student, assignments = parse_title(title)
            fmt = classify_title_format(title)

            issues.append(
                Issue(
                    issue_id=issue_id,
                    state=state,
                    title=title,
                    created_at_utc=created_at_utc,
                    student=student,
                    assignments=assignments,
                    format_class=fmt,
                )
            )
    return issues


def parse_students_from_readme(readme_text: str) -> list[str]:
    # Parses rows like: | [Name](...) |
    names: list[str] = []
    for line in readme_text.splitlines():
        if line.startswith("| [") and "](" in line:
            m = re.match(r"\|\s*\[([^\]]+)\]\(", line)
            if m:
                names.append(normalize_spaces(m.group(1)))
    return names


def human_delta(hours: float) -> str:
    sign = "-" if hours < 0 else ""
    h = abs(hours)
    days = int(h // 24)
    rem = h - 24 * days
    if days:
        return f"{sign}{days}d {rem:.1f}h"
    return f"{sign}{rem:.1f}h"


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

    # assignment -> student -> earliest submission time (UTC)
    submissions: dict[str, dict[str, dt.datetime]] = defaultdict(dict)
    for iss in issues:
        for a in iss.assignments:
            prev = submissions[a].get(iss.student)
            if prev is None or iss.created_at_utc < prev:
                submissions[a][iss.student] = iss.created_at_utc

    # What assignments to include?
    # Use the deadlines dict keys (since that’s the “truth” now),
    # plus anything detected in subjects (to be safe).
    detected = set(submissions.keys())
    all_assignments = sorted(
        set(deadlines.keys()) | detected,
        key=lambda a: (0, int(a[3:])) if re.fullmatch(r"day\d\d", a) else (1, a),
    )

    fmt_counts = Counter(i.format_class for i in issues)

    lines: list[str] = []
    lines.append("# Submission report\n")
    lines.append(f"Generated at (UTC): {dt.datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M')}\n")
    lines.append(f"Roster size: **{len(roster_set)}**\n")

    # Overall table
    lines.append("## Overall coverage (per assignment)\n")
    lines.append("| Assignment | Deadline (Asia/Jerusalem) | Submitted | Missing | Late |")
    lines.append("|---|---|---:|---:|---:|")

    overall = []
    for a in all_assignments:
        dl = deadlines.get(a)
        submap = submissions.get(a, {})
        submitted = set(submap.keys())
        missing = roster_set - submitted
        late = "—"
        dl_local = "—"
        if dl is not None:
            dl_local = dl.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
            late = str(sum(1 for t in submap.values() if t > dl))
        overall.append((a, dl_local, f"{len(submitted)}/{len(roster_set)}", str(len(missing)), late))

    for a, dl_local, sub_s, miss_s, late_s in overall:
        lines.append(f"| {a} | {dl_local} | {sub_s} | {miss_s} | {late_s} |")
    lines.append("")

    # Popularity
    lines.append("## Subject/title format popularity\n")
    lines.append("| Format | Count |")
    lines.append("|---|---:|")
    for fmt, c in fmt_counts.most_common():
        lines.append(f"| {fmt} | {c} |")
    lines.append("")

    # Details per assignment (this is the “includes everything you asked” part)
    for a in all_assignments:
        dl = deadlines.get(a)
        submap = submissions.get(a, {})
        submitted_students = set(submap.keys())
        missing = sorted(roster_set - submitted_students)

        lines.append(f"## {a}\n")
        if dl is None:
            lines.append("**Deadline:** (not defined in `deadlines` dictionary)\n")
        else:
            lines.append(f"**Deadline (Asia/Jerusalem):** {dl.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M')}  ")
            lines.append(f"**Deadline (UTC):** {dl.strftime('%Y-%m-%d %H:%M')}\n")

        lines.append(f"- **Submitted:** {len(submitted_students)}/{len(roster_set)}")
        lines.append(f"- **Missing:** {len(missing)}")
        if dl is not None:
            lines.append(f"- **Late:** {sum(1 for t in submap.values() if t > dl)}")
        lines.append("")

        # Missing list
        if missing:
            lines.append("### Missing students\n")
            for s in missing:
                lines.append(f"- {s}")
            lines.append("")

        # Late list + distribution
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
                for hours, student, t_utc in late_list[:20]:
                    t_local = t_utc.astimezone(LOCAL_TZ)
                    lines.append(f"| {student} | {t_local.strftime('%Y-%m-%d %H:%M')} | {human_delta(hours)} |")
                if len(late_list) > 20:
                    lines.append(f"\n(Showing 20 of {len(late_list)} late submissions.)\n")
                else:
                    lines.append("")

            # Distribution
            p10 = percentile(deltas, 0.10)
            p50 = percentile(deltas, 0.50)
            p90 = percentile(deltas, 0.90)

            lines.append("### Distribution vs deadline (hours)\n")
            lines.append(f"- **P10:** {human_delta(p10)}")
            lines.append(f"- **Median (P50):** {human_delta(p50)}")
            lines.append(f"- **P90:** {human_delta(p90)}")
            lines.append(f"- **Earliest:** {human_delta(deltas[0])}")
            lines.append(f"- **Latest:** {human_delta(deltas[-1])}\n")

            bins = [
                (-10_000, -168, "≤ -7d"),
                (-168, -48, "(-7d, -2d]"),
                (-48, -24, "(-2d, -1d]"),
                (-24, -6, "(-1d, -6h]"),
                (-6, 0, "(-6h, on-time]"),
                (0, 6, "(0, +6h]"),
                (6, 24, "(+6h, +1d]"),
                (24, 48, "(+1d, +2d]"),
                (48, 168, "(+2d, +7d]"),
                (168, 10_000, "> +7d"),
            ]

            bucket_counts = Counter()
            for h in deltas:
                for lo, hi, label in bins:
                    if lo < h <= hi:
                        bucket_counts[label] += 1
                        break

            def pct(x: int) -> str:
                return f"{100.0 * x / len(deltas):.1f}%"

            lines.append("| Time vs deadline | Count | Percent |")
            lines.append("|---|---:|---:|")
            for _, _, label in bins:
                c = bucket_counts.get(label, 0)
                lines.append(f"| {label} | {c} | {pct(c)} |")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", default="day09/subjects.txt", help="Path to day09/subjects.txt")
    parser.add_argument("--readme", default=None, help="Optional path to README.md to parse roster")
    parser.add_argument("--out", default="report.md", help="Output report path")
    parser.add_argument("--stdout", action="store_true", help="Print report instead of writing a file")
    args = parser.parse_args()

    issues = read_subjects(args.subjects)

    roster: list[str] = []
    if args.readme:
        with open(args.readme, "r", encoding="utf-8", errors="replace") as f:
            roster = parse_students_from_readme(f.read())

    # fallback roster if README roster wasn't found
    if not roster:
        roster = sorted({i.student for i in issues if i.student != "UNKNOWN"})
        # still allow UNKNOWN but don't count it as a roster person

    report_md = build_report(issues, roster)

    if args.stdout:
        print(report_md)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Wrote report to: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
