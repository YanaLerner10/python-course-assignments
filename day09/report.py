#!/usr/bin/env python3
"""
Day09 report generator

Reads:
  - day09/subjects.txt : tab-separated list of GitHub issues (id, state, title, ..., created_at)
  - README.md          : course README containing deadlines and the student roster table

Outputs:
  - report.md          : a Markdown report (or prints to stdout with --stdout)

Usage:
  python day09_report.py --subjects day09/subjects.txt --readme README.md --out report.md
  python day09_report.py --subjects day09/subjects.txt --readme README.md --stdout

Notes:
  - Deadlines in README are assumed to be in Asia/Jerusalem time (course local time).
  - Issue timestamps are assumed to be UTC ISO strings ending with 'Z' (e.g. 2026-01-03T18:44:38Z).
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Asia/Jerusalem")
UTC = dt.timezone.utc

DAY_RE = re.compile(r"\bday\s*0?(\d{1,2})\b", re.IGNORECASE)

NAME_PATTERNS = [
    re.compile(r"\bby\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s*[-:]\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bday\s*\d{1,2}\s+(.+)$", re.IGNORECASE),
    re.compile(r"proposal\s+for\s+final\s+project[-:]\s*(.+)$", re.IGNORECASE),
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


def normalize_name(name: str) -> str:
    # Keep original capitalization (it is useful), but normalize whitespace.
    return normalize_spaces(name)


def parse_issue_created_at(s: str) -> dt.datetime:
    # Expected: 2026-01-03T18:44:38Z
    # We parse it as UTC.
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s).astimezone(UTC)


def classify_title_format(title: str) -> str:
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
    """
    Returns: (student_name, assignments)
    assignments include dayXX and/or 'final_project_proposal'
    """
    t = normalize_spaces(title)

    # student name
    student = None
    for pat in NAME_PATTERNS:
        m = pat.search(t)
        if m:
            student = normalize_name(m.group(1))
            break
    if student is None:
        # fallback (should be rare)
        student = "UNKNOWN"

    assignments: list[str] = []

    tl = t.lower()
    if "final project proposal" in tl or "proposal for final project" in tl:
        assignments.append("final_project_proposal")

    for n in DAY_RE.findall(t):
        assignments.append(f"day{int(n):02d}")

    # de-dup preserve order
    seen = set()
    uniq: list[str] = []
    for a in assignments:
        if a not in seen:
            uniq.append(a)
            seen.add(a)

    return student, tuple(uniq)


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
    """
    Extracts student names from the 'Students' table in README.md.
    Looks for markdown table rows starting with: | [Name](
    """
    names: list[str] = []
    for line in readme_text.splitlines():
        if line.startswith("| [") and "](" in line:
            m = re.match(r"\|\s*\[([^\]]+)\]\(", line)
            if m:
                names.append(normalize_name(m.group(1)))
    return names


def parse_deadlines_from_readme(readme_text: str) -> dict[str, dt.datetime]:
    """
    Extract deadlines of the form:
      * Dead-line: YYYY.MM.DD HH:MM
    under:
      ### Assignment (day X)

    Returns dict: {"day01": deadline_utc, ...}

    If some day has "TBD" or no deadline, it's omitted.
    """
    deadlines: dict[str, dt.datetime] = {}

    section_pat = re.compile(r"### Assignment \(day\s*(\d+)\)(.*?)(?:\n## |\Z)", re.S)
    for m in section_pat.finditer(readme_text):
        day_num = int(m.group(1))
        body = m.group(2)
        dm = re.search(r"Dead-line:\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})", body)
        if not dm:
            continue
        local_naive = dt.datetime.strptime(dm.group(1), "%Y.%m.%d %H:%M")
        deadline_utc = local_naive.replace(tzinfo=LOCAL_TZ).astimezone(UTC)
        deadlines[f"day{day_num:02d}"] = deadline_utc

    # Also parse project proposal/submission deadlines if present (nice-to-have)
    proj_pat = re.compile(
        r"\*\s*Project\s+(proposal|submission)\s+dead-line:\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})",
        re.IGNORECASE,
    )
    for pm in proj_pat.finditer(readme_text):
        kind = pm.group(1).lower()
        local_naive = dt.datetime.strptime(pm.group(2), "%Y.%m.%d %H:%M")
        deadline_utc = local_naive.replace(tzinfo=LOCAL_TZ).astimezone(UTC)
        deadlines[f"project_{kind}"] = deadline_utc

    return deadlines


def human_timedelta(hours: float) -> str:
    sign = "-" if hours < 0 else ""
    h = abs(hours)
    days = int(h // 24)
    rem_h = h - days * 24
    if days > 0:
        return f"{sign}{days}d {rem_h:.1f}h"
    return f"{sign}{rem_h:.1f}h"


def build_report(issues: list[Issue], students: list[str], deadlines: dict[str, dt.datetime]) -> str:
    roster = set(students)

    # submissions[assignment][student] = earliest submission time
    submissions: dict[str, dict[str, dt.datetime]] = defaultdict(dict)

    for iss in issues:
        for a in iss.assignments:
            prev = submissions[a].get(iss.student)
            if prev is None or iss.created_at_utc < prev:
                submissions[a][iss.student] = iss.created_at_utc

    # Determine which assignments to report:
    # - all "dayXX" that have deadlines
    # - plus project proposal/submission deadlines if present
    def sort_key(a: str) -> tuple[int, str]:
        m = re.match(r"day(\d{2})$", a)
        if m:
            return (0, m.group(1))
        return (1, a)

    assignments_to_report = sorted(deadlines.keys(), key=sort_key)

    # Popularity of title formats
    fmt_counts = Counter(iss.format_class for iss in issues)

    # Prepare report
    lines: list[str] = []
    lines.append("# Submission report\n")
    lines.append(f"Generated at (UTC): {dt.datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("## What this report includes\n")
    lines.append("- Missing submissions per assignment\n- Late submissions per assignment\n- Submission-time distribution vs deadline\n- Subject/title format popularity\n")

    # Subject format popularity
    lines.append("## Subject/title format popularity\n")
    lines.append("| Format | Count |")
    lines.append("|---|---:|")
    for fmt, c in fmt_counts.most_common():
        lines.append(f"| {fmt} | {c} |")
    lines.append("")

    # Per assignment: missing + late + distribution
    for a in assignments_to_report:
        deadline = deadlines[a]
        submap = submissions.get(a, {})
        submitted_students = set(submap.keys())
        missing = sorted(roster - submitted_students)

        # Compute deltas (hours) for submissions we have
        deltas = []
        late_list = []
        for student, t_utc in submap.items():
            hours = (t_utc - deadline).total_seconds() / 3600.0
            deltas.append(hours)
            if hours > 0:
                late_list.append((hours, student, t_utc))

        late_list.sort(reverse=True)

        lines.append(f"## {a}\n")
        lines.append(f"**Deadline (Asia/Jerusalem):** {deadline.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M')}  ")
        lines.append(f"**Deadline (UTC):** {deadline.strftime('%Y-%m-%d %H:%M')}\n")

        lines.append(f"- **Submitted:** {len(submitted_students)}/{len(roster)}")
        lines.append(f"- **Missing:** {len(missing)}")
        lines.append(f"- **Late submissions:** {len(late_list)}\n")

        if missing:
            lines.append("### Missing students\n")
            # Print in compact columns (bullets)
            for s in missing:
                lines.append(f"- {s}")
            lines.append("")

        if late_list:
            lines.append("### Latest submissions (most late first)\n")
            lines.append("| Student | Submitted (UTC) | Late by |")
            lines.append("|---|---|---:|")
            for hours, student, t_utc in late_list[:15]:
                lines.append(f"| {student} | {t_utc.strftime('%Y-%m-%d %H:%M')} | {human_timedelta(hours)} |")
            if len(late_list) > 15:
                lines.append(f"\n(Showing 15 of {len(late_list)} late submissions.)\n")
            else:
                lines.append("")

        if deltas:
            deltas.sort()
            # Histogram bins (hours relative to deadline)
            bins = [
                (-10_000, -168, "≤ -7d (very early)"),
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

            lines.append("### Distribution vs deadline\n")
            lines.append(f"- **Median:** {human_timedelta(deltas[len(deltas)//2])}")
            lines.append(f"- **Min (earliest):** {human_timedelta(deltas[0])}")
            lines.append(f"- **Max (latest):** {human_timedelta(deltas[-1])}\n")

            lines.append("| Time vs deadline | Count | Percent |")
            lines.append("|---|---:|---:|")
            for _, _, label in bins:
                c = bucket_counts.get(label, 0)
                lines.append(f"| {label} | {c} | {pct(c)} |")
            lines.append("")

    # Appendix: raw counts by assignment (including ones without deadlines)
    lines.append("## Appendix: assignments detected in issue titles\n")
    detected = Counter()
    for iss in issues:
        for a in iss.assignments:
            detected[a] += 1
    lines.append("| Assignment key | Issue count |")
    lines.append("|---|---:|")
    for a, c in detected.most_common():
        lines.append(f"| {a} | {c} |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subjects", default="day09/subjects.txt", help="Path to day09/subjects.txt")
    parser.add_argument("--readme", default="README.md", help="Path to README.md")
    parser.add_argument("--out", default="report.md", help="Where to write the report (ignored with --stdout)")
    parser.add_argument("--stdout", action="store_true", help="Print report to stdout instead of writing a file")
    args = parser.parse_args()

    with open(args.readme, "r", encoding="utf-8", errors="replace") as f:
        readme_text = f.read()

    students = parse_students_from_readme(readme_text)
    deadlines = parse_deadlines_from_readme(readme_text)
    issues = read_subjects(args.subjects)

    report_md = build_report(issues, students, deadlines)

    if args.stdout:
        print(report_md)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"Wrote report to: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
