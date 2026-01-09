#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Asia/Jerusalem")
UTC = dt.timezone.utc

# Matches: Day1, Day 1, Day01, day 01, etc.
DAY_RE = re.compile(r"\bday\s*0?(\d{1,2})\b", re.IGNORECASE)

# Student name extraction patterns from subject/title
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
    return normalize_spaces(name)


def parse_issue_created_at(s: str) -> dt.datetime:
    # e.g. 2026-01-03T18:44:38Z
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
    t = normalize_spaces(title)

    student = None
    for pat in NAME_PATTERNS:
        m = pat.search(t)
        if m:
            student = normalize_name(m.group(1))
            break
    if student is None:
        student = "UNKNOWN"

    assignments: list[str] = []
    tl = t.lower()
    if "final project proposal" in tl or "proposal for final project" in tl:
        assignments.append("final_project_proposal")

    for n in DAY_RE.findall(t):
        assignments.append(f"day{int(n):02d}")

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
    # Parses the Markdown table rows: | [Name](...) |
    names: list[str] = []
    for line in readme_text.splitlines():
        if line.startswith("| [") and "](" in line:
            m = re.match(r"\|\s*\[([^\]]+)\]\(", line)
            if m:
                names.append(normalize_name(m.group(1)))
    return names


def parse_deadlines_from_readme(readme_text: str) -> dict[str, dt.datetime]:
    """
    Extracts '* Dead-line: YYYY.MM.DD HH:MM' for each '### Assignment (day X)' block.
    IMPORTANT: stop the block at the next '### Assignment' (not '##'), otherwise parsing may break
    depending on README structure.
    """
    deadlines: dict[str, dt.datetime] = {}

    section_pat = re.compile(
        r"### Assignment \(day\s*(\d+)\)(.*?)(?=\n### Assignment|\n## |\Z)",
        re.S,
    )
    for m in section_pat.finditer(readme_text):
        day_num = int(m.group(1))
        body = m.group(2)
        dm = re.search(r"Dead-line:\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})", body)
        if not dm:
            continue
        local_naive = dt.datetime.strptime(dm.group(1), "%Y.%m.%d %H:%M")
        deadlines[f"day{day_num:02d}"] = local_naive.replace(tzinfo=LOCAL_TZ).astimezone(UTC)

    # Project deadlines are written explicitly in the Day 9 section too
    for key, pat in [
        ("project_proposal", r"Project proposal dead-line:\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})"),
        ("project_submission", r"Project submission dead-line:\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})"),
    ]:
        pm = re.search(pat, readme_text)
        if pm:
            local_naive = dt.datetime.strptime(pm.group(1), "%Y.%m.%d %H:%M")
            deadlines[key] = local_naive.replace(tzinfo=LOCAL_TZ).astimezone(UTC)

    return deadlines


def human_delta_hours(hours: float) -> str:
    sign = "-" if hours < 0 else ""
    h = abs(hours)
    days = int(h // 24)
    rem = h - days * 24
    if days:
        return f"{sign}{days}d {rem:.1f}h"
    return f"{sign}{rem:.1f}h"


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    # p in [0,1]
    idx = (len(sorted_vals) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def build_report(issues: list[Issue], students: list[str], deadlines: dict[str, dt.datetime]) -> str:
    roster = set(students)

    # assignment -> student -> earliest submission time
    submissions: dict[str, dict[str, dt.datetime]] = defaultdict(dict)
    for iss in issues:
        for a in iss.assignments:
            prev = submissions[a].get(iss.student)
            if prev is None or iss.created_at_utc < prev:
                submissions[a][iss.student] = iss.created_at_utc

    # Assignments we will report:
    # union of (detected in subjects) and (deadlines in README)
    detected_assignments = set(submissions.keys())
    all_assignments = sorted(
        detected_assignments | set(deadlines.keys()),
        key=lambda a: (0, int(a[3:])) if re.fullmatch(r"day\d\d", a) else (1, a),
    )

    fmt_counts = Counter(iss.format_class for iss in issues)

    # Overall coverage table at the top
    overall_rows = []
    for a in all_assignments:
        submap = submissions.get(a, {})
        submitted = set(submap.keys())
        missing = roster - submitted
        dl = deadlines.get(a)
        late = 0
        if dl:
            for _, t in submap.items():
                if t > dl:
                    late += 1
        overall_rows.append((a, dl, len(submitted), len(missing), late))

    lines: list[str] = []
    lines.append("# Submission report\n")
    lines.append(f"Generated at (UTC): {dt.datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M')}\n")

    lines.append("## Overall coverage (per assignment)\n")
    lines.append("| Assignment | Deadline (Asia/Jerusalem) | Submitted | Missing | Late |")
    lines.append("|---|---|---:|---:|---:|")
    for a, dl, sub_n, miss_n, late_n in overall_rows:
        dl_str = "—" if dl is None else dl.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        lines.append(f"| {a} | {dl_str} | {sub_n}/{len(roster)} | {miss_n} | {late_n if dl else '—'} |")
    lines.append("")

    lines.append("## Subject/title format popularity\n")
    lines.append("| Format | Count |")
    lines.append("|---|---:|")
    for fmt, c in fmt_counts.most_common():
        lines.append(f"| {fmt} | {c} |")
    lines.append("")

    # Per-assignment detailed sections (this is what your pasted report is missing)
    for a in all_assignments:
        submap = submissions.get(a, {})
        submitted_students = set(submap.keys())
        missing = sorted(roster - submitted_students)

        dl = deadlines.get(a)

        lines.append(f"## {a}\n")
        if dl is None:
            lines.append("**Deadline:** not found in README (e.g. `TBD`).\n")
        else:
            lines.append(f"**Deadline (Asia/Jerusalem):** {dl.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M')}  ")
            lines.append(f"**Deadline (UTC):** {dl.strftime('%Y-%m-%d %H:%M')}\n")

        lines.append(f"- **Submitted:** {len(submitted_students)}/{len(roster)}")
        lines.append(f"- **Missing:** {len(missing)}")
        if dl is not None:
            late_count = sum(1 for t in submap.values() if t > dl)
            lines.append(f"- **Late:** {late_count}")
        lines.append("")

        if missing:
            lines.append("### Missing students\n")
            for s in missing:
                lines.append(f"- {s}")
            lines.append("")

        # Late submissions details + distribution only if deadline exists
        if dl is not None and submap:
            deltas = []
            late_list = []
            for student, t_utc in submap.items():
                hours = (t_utc - dl).total_seconds() / 3600.0
                deltas.append(hours)
                if hours > 0:
                    late_list.append((hours, student, t_utc))
            deltas.sort()
            late_list.sort(reverse=True)

            if late_list:
                lines.append("### Late submissions (most late first)\n")
                lines.append("| Student | Submitted (Asia/Jerusalem) | Submitted (UTC) | Late by |")
                lines.append("|---|---|---|---:|")
                for hours, student, t_utc in late_list[:20]:
                    t_local = t_utc.astimezone(LOCAL_TZ)
                    lines.append(
                        f"| {student} | {t_local.strftime('%Y-%m-%d %H:%M')} | {t_utc.strftime('%Y-%m-%d %H:%M')} | {human_delta_hours(hours)} |"
                    )
                if len(late_list) > 20:
                    lines.append(f"\n(Showing 20 of {len(late_list)} late submissions.)\n")
                else:
                    lines.append("")

            # Distribution summary
            p10 = percentile(deltas, 0.10)
            p50 = percentile(deltas, 0.50)
            p90 = percentile(deltas, 0.90)

            lines.append("### Distribution vs deadline (hours)\n")
            lines.append(f"- **P10:** {human_delta_hours(p10)}")
            lines.append(f"- **Median (P50):** {human_delta_hours(p50)}")
            lines.append(f"- **P90:** {human_delta_hours(p90)}")
            lines.append(f"- **Earliest:** {human_delta_hours(deltas[0])}")
            lines.append(f"- **Latest:** {human_delta_hours(deltas[-1])}\n")

            # Histogram bins (hours relative to deadline)
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

    # Appendix: raw detection
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
    parser.add_argument("--subjects", default="day09/subjects.txt")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--out", default="report.md")
    parser.add_argument("--stdout", action="store_true")
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
