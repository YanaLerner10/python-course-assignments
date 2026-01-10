from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import matplotlib.pyplot as plt


TZ = ZoneInfo("Asia/Jerusalem")


# ----------------------------
# Parsing README: deadlines + student roster
# ----------------------------

DEADLINE_RE = re.compile(r"Dead-line:\s*(\d{4}\.\d{2}\.\d{2})\s*(\d{2}:\d{2})")
DAY_SECTION_SPLIT_RE = re.compile(r"\n## Day (\d+)\n")
STUDENT_ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\(")  # captures student name in table row


@dataclass(frozen=True)
class Deadline:
    day: int
    due_local: datetime


def parse_readme_deadlines(readme_text: str) -> dict[int, datetime]:
    """
    Returns: day -> deadline datetime in Asia/Jerusalem timezone
    Notes:
      - Day 1 has two deadlines (assignment + amendment). We take the FIRST one inside Day 1 section.
    """
    parts = DAY_SECTION_SPLIT_RE.split(readme_text)
    # parts looks like: [preamble, "1", day1content, "2", day2content, ...]
    deadlines: dict[int, datetime] = {}

    for i in range(1, len(parts), 2):
        day = int(parts[i])
        content = parts[i + 1]
        found = DEADLINE_RE.findall(content)
        if not found:
            continue

        # Take FIRST deadline in that Day section
        d_str, t_str = found[0]
        due = datetime.strptime(f"{d_str} {t_str}", "%Y.%m.%d %H:%M").replace(tzinfo=TZ)
        deadlines[day] = due

    return deadlines


def parse_readme_students(readme_text: str) -> list[str]:
    """
    Parses the student roster table rows under '## Students' section.
    We collect any markdown table row starting with: | [Name](
    """
    students: list[str] = []
    for line in readme_text.splitlines():
        m = STUDENT_ROW_RE.match(line.strip())
        if m:
            students.append(m.group(1).strip())
    # Remove duplicates while preserving order
    seen = set()
    uniq = []
    for s in students:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


# ----------------------------
# Parsing subjects.csv
# ----------------------------

DAY_RE = re.compile(r"(?i)\bday\s*0?(\d{1,2})\b")
BY_RE = re.compile(r"(?i)\bby\b\s*(.+)$")


def extract_day(title: str) -> int | None:
    m = DAY_RE.search(title or "")
    return int(m.group(1)) if m else None


def extract_name(title: str) -> str | None:
    title = title or ""
    m = BY_RE.search(title)
    if m:
        return m.group(1).strip() or None

    # fallback: sometimes "day03 Your Name"
    m = DAY_RE.search(title)
    if m:
        rest = title[m.end():].strip(" -:_")
        return rest.strip() or None

    return None


def detect_subject_format(title: str) -> str:
    """
    Categorize the subject/title format (useful for the 'Popularity of subject formats' idea).
    """
    t = title or ""

    if re.search(r"(?i)\bfinal\s+project\s+proposal\b", t):
        return "Final Project proposal ..."
    if re.search(r"(?i)\bfinal\s+project\b", t):
        return "Final Project (other)"
    if re.search(r"(?i)\bday\s*\d+\s+by\b", t):
        return "DayXX by Name"
    if re.search(r"(?i)\bday\s*\d+\b", t):
        return "DayXX (other)"
    return "Other / unrecognized"


def load_subjects_csv(subjects_path: Path) -> pd.DataFrame:
    """
    Handles the common export format where the file has no header and has 5 columns:
      issue_number, state, title, (maybe empty), created_at_iso_z
    """
    df = pd.read_csv(subjects_path, header=None)

    # Normalize columns to 5 (pad if needed)
    while df.shape[1] < 5:
        df[df.shape[1]] = pd.NA

    df = df.iloc[:, :5].copy()
    df.columns = ["issue", "state", "title", "extra", "created_at"]

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["title"] = df["title"].astype(str)

    df["day"] = df["title"].apply(extract_day)
    df["student"] = df["title"].apply(extract_name)
    df["format"] = df["title"].apply(detect_subject_format)

    df["created_local"] = df["created_at"].dt.tz_convert(TZ)
    return df


# ----------------------------
# Reporting
# ----------------------------

def hours_delta(a: datetime, b: datetime) -> float:
    return (a - b).total_seconds() / 3600.0


def write_report(
    out_md: Path,
    plots_dir: Path,
    students: list[str],
    deadlines: dict[int, datetime],
    issues: pd.DataFrame,
) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Submission Report\n")
    lines.append(f"Generated at: {datetime.now(tz=TZ).strftime('%Y-%m-%d %H:%M %Z')}\n")
    lines.append("## What this report contains\n")
    lines.append("- Missing submissions per day (based on the official student roster in README)\n")
    lines.append("- Late submissions per day (based on README deadlines)\n")
    lines.append("- Histogram of submission time relative to the deadline (hours)\n")
    lines.append("- Subject-line format statistics\n")

    # Subject format popularity (whole dataset)
    fmt_counts = issues["format"].value_counts(dropna=False)
    lines.append("\n## Subject-line formats (all issues)\n")
    lines.append("| Format | Count |\n|---|---:|\n")
    for fmt, cnt in fmt_counts.items():
        lines.append(f"| {fmt} | {int(cnt)} |\n")

    # Focus: assignments with deadlines (day -> due)
    lines.append("\n## Per-assignment (per Day) analysis\n")

    # Filter issues that look like day submissions
    day_issues = issues.dropna(subset=["day", "student"]).copy()
    day_issues["day"] = day_issues["day"].astype(int)

    # For each student/day pick earliest issue (first submission)
    day_issues = day_issues.sort_values("created_local")
    first_sub = day_issues.groupby(["day", "student"], as_index=False).first()

    for day in sorted(deadlines.keys()):
        due = deadlines[day]
        lines.append(f"\n### Day {day}\n")
        lines.append(f"Deadline (Asia/Jerusalem): **{due.strftime('%Y-%m-%d %H:%M')}**\n\n")

        submitted = first_sub[first_sub["day"] == day].copy()
        submitted_students = sorted(set(s for s in submitted["student"].dropna().tolist()))

        missing = [s for s in students if s not in submitted_students]

        # Missing list
        lines.append("**Missing submissions:**\n\n")
        if missing:
            for s in missing:
                lines.append(f"- {s}\n")
        else:
            lines.append("- None 🎉\n")

        # Late table
        lines.append("\n**Late submissions:**\n\n")
        if submitted.empty:
            lines.append("_No submissions found for this day in subjects file._\n")
            continue

        submitted["delta_hours"] = submitted["created_local"].apply(lambda x: hours_delta(x, due))
        late = submitted[submitted["delta_hours"] > 0].sort_values("delta_hours", ascending=False)

        if late.empty:
            lines.append("- None 🎉\n")
        else:
            lines.append("| Student | Submitted (local time) | Hours after deadline |\n")
            lines.append("|---|---|---:|\n")
            for _, row in late.iterrows():
                lines.append(
                    f"| {row['student']} | {row['created_local'].strftime('%Y-%m-%d %H:%M')} | {row['delta_hours']:.2f} |\n"
                )

        # Histogram for this day
        # include on-time and late; delta<0 means early
        deltas = submitted["delta_hours"].dropna().to_list()
        if deltas:
            plt.figure()
            plt.hist(deltas, bins=20)
            plt.title(f"Day {day}: submission time relative to deadline (hours)")
            plt.xlabel("Hours (submission_time - deadline)")
            plt.ylabel("Number of students")
            plot_path = plots_dir / f"day{day:02d}_hist.png"
            plt.tight_layout()
            plt.savefig(plot_path, dpi=150)
            plt.close()
            lines.append(f"\nHistogram: `output/plots/{plot_path.name}`\n")

    out_md.write_text("".join(lines), encoding="utf-8")


# ----------------------------
# CLI
# ----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a submission report from README.md deadlines and subjects.csv issue list."
    )
    parser.add_argument("--readme", type=Path, default=Path("README.md"), help="Path to README.md input")
    parser.add_argument("--subjects", type=Path, default=Path("subjects.csv"), help="Path to subjects.csv input")
    parser.add_argument("--out", type=Path, default=Path("output/report.md"), help="Path to output report.md")

    args = parser.parse_args()

    if not args.readme.exists():
        raise SystemExit(f"README not found: {args.readme}")
    if not args.subjects.exists():
        raise SystemExit(f"Subjects file not found: {args.subjects}")

    readme_text = args.readme.read_text(encoding="utf-8")
    deadlines = parse_readme_deadlines(readme_text)
    students = parse_readme_students(readme_text)

    issues = load_subjects_csv(args.subjects)

    plots_dir = args.out.parent / "plots"
    write_report(args.out, plots_dir, students, deadlines, issues)

    print(f"✅ Report created: {args.out}")
    print(f"✅ Plots in: {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
