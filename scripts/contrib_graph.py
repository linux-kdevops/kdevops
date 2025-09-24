#!/usr/bin/env python3
"""
kdevops Contribution Visualization Tool
Generates matplotlib graphs showing contributor activity for specified time periods
"""

import argparse
import subprocess
import sys
import re
from datetime import datetime, date
import os
import calendar
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

# Set style for better looking plots
plt.style.use("seaborn-v0_8-darkgrid")
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.facecolor"] = "#f8f9fa"
plt.rcParams["axes.facecolor"] = "#ffffff"
plt.rcParams["grid.alpha"] = 0.2


def run_git_command(cmd):
    """Execute git command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {cmd}")
        print(f"Error: {e}")
        sys.exit(1)


def get_date_range(year=None, month=None):
    """Get appropriate date range for git log"""
    if year:
        if month:
            # Start from specific month
            start_date = f"{year}-{month:02d}-01"
            # Use current date as end date if analyzing current year
            current_date = datetime.now()
            if int(year) == current_date.year:
                # For current year, don't go beyond current date
                end_date = current_date.strftime("%Y-%m-%d")
            else:
                end_date = f"{year}-12-31"
        else:
            # Full year
            start_date = f"{year}-01-01"
            current_date = datetime.now()
            if int(year) == current_date.year:
                # For current year, don't go beyond current date
                end_date = current_date.strftime("%Y-%m-%d")
            else:
                end_date = f"{year}-12-31"
        return start_date, end_date
    else:
        # All history - no date filtering
        return None, None


def get_contribution_data(year=None, month=None):
    """Extract contribution data from git log"""
    start_date, end_date = get_date_range(year, month)

    # Build git log command
    if start_date and end_date:
        date_filter = f'--since="{start_date}" --until="{end_date}"'
        if month:
            month_names = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            # Determine actual end month from end_date
            end_year, end_month = end_date.split("-")[:2]
            end_month_int = int(end_month)
            if end_month_int == 12:
                period_desc = f"for {year} ({month_names[month-1]}-Dec)"
            else:
                period_desc = f"for {year} ({month_names[month-1]}-{month_names[end_month_int-1]})"
        else:
            period_desc = f"for {year}"
    elif start_date:
        date_filter = f'--since="{start_date}"'
        period_desc = f"since {start_date}"
    elif end_date:
        date_filter = f'--until="{end_date}"'
        period_desc = f"until {end_date}"
    else:
        date_filter = ""
        period_desc = "all time"

    print(f"📊 Analyzing kdevops contributions {period_desc}...")

    # Get contributor totals
    cmd = f'git log {date_filter} --pretty=format:"%an" | sort | uniq -c | sort -nr'
    output = run_git_command(cmd)

    contributors_total = {}
    for line in output.split("\n"):
        if line.strip():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                count, author = int(parts[0]), parts[1]
                contributors_total[author] = count

    # Get monthly data with full date info for proper filtering
    # Use commit date (--date) instead of author date to ensure consistency with date_filter
    cmd = f'git log {date_filter} --pretty=format:"%an|%cd" --date=format:"%Y-%m"'
    output = run_git_command(cmd)

    monthly_data = defaultdict(int)

    for line in output.split("\n"):
        if line.strip() and "|" in line:
            author, date_str = line.strip().split("|", 1)
            if "-" in date_str:
                try:
                    year_month = date_str.strip()
                    year_str, month_str = year_month.split("-")
                    commit_year = int(year_str)
                    month_int = int(month_str)

                    # Just include all commits - no filtering
                    monthly_data[(author, month_int)] += 1
                except (ValueError, IndexError):
                    continue

    # Track Generated-by usage over time
    cmd = (
        f'git log {date_filter} --grep="Generated-by:" '
        '--pretty=format:"%cd" --date=format:"%Y-%m"'
    )
    output = run_git_command(cmd)

    generated_by_monthly = defaultdict(int)

    for line in output.split("\n"):
        entry = line.strip()
        if entry:
            try:
                month_date = datetime.strptime(f"{entry}-01", "%Y-%m-%d").date()
                generated_by_monthly[month_date] += 1
            except ValueError:
                continue

    # Get total commits for period calculation
    cmd = f"git log {date_filter} --oneline | wc -l"
    total_commits = int(run_git_command(cmd))

    # Get AI-boom marker date - June 27, 2025
    try:
        ai_boom_date = datetime(2025, 6, 27)
        # Calculate position within the month (June = month 6)
        # Day 27 out of 30 days in June
        ai_boom_marker = (
            ai_boom_date.month + (ai_boom_date.day - 1) / 30.0
        )  # Fractional month position
        # Only include marker if it falls within the analyzed time period
        if year:
            # For specific year, only show if marker is in that year
            if ai_boom_date.year != int(year):
                ai_boom_marker = None
        # For all-time, always include the marker if the commit exists
    except Exception as e:
        ai_boom_marker = None

    return (
        contributors_total,
        dict(monthly_data),
        total_commits,
        period_desc,
        ai_boom_marker,
        dict(generated_by_monthly),
    )


def create_contribution_graphs(
    contributors_total,
    monthly_data,
    total_commits,
    period_desc,
    ai_boom_marker=None,
    generated_by_monthly=None,
    year=None,
    month=None,
):
    """Create comprehensive visualization graphs"""

    if generated_by_monthly is None:
        generated_by_monthly = {}

    # Determine output filename
    if year:
        if month:
            month_names = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            # Check if this is current year to determine actual end month
            current_date = datetime.now()
            if int(year) == current_date.year:
                end_month = current_date.month
                if end_month == 12:
                    output_base = f"kdevops_contributions_{year}_{month_names[month-1].lower()}_dec"
                    title_suffix = f" ({year}, {month_names[month-1]}-Dec)"
                else:
                    output_base = f"kdevops_contributions_{year}_{month_names[month-1].lower()}_{month_names[end_month-1].lower()}"
                    title_suffix = (
                        f" ({year}, {month_names[month-1]}-{month_names[end_month-1]})"
                    )
            else:
                output_base = (
                    f"kdevops_contributions_{year}_{month_names[month-1].lower()}_dec"
                )
                title_suffix = f" ({year}, {month_names[month-1]}-Dec)"
        else:
            output_base = f"kdevops_contributions_{year}"
            title_suffix = f" ({year})"
    else:
        output_base = "kdevops_contributions_all_time"
        title_suffix = " (All Time)"

    # Create figure with multiple subplots and better styling
    fig = plt.figure(figsize=(24, 16), facecolor="#f8f9fa")
    gs = fig.add_gridspec(
        3,
        3,
        height_ratios=[1, 1, 1.1],
        hspace=0.35,
        wspace=0.3,
    )
    fig.suptitle(
        f"kdevops Contribution Analysis{title_suffix}",
        fontsize=24,
        fontweight="bold",
        y=0.985,
        color="#2c3e50",
    )

    if not contributors_total:
        print("⚠️  No contributions found for the specified period")
        return None

    # 1. Total Contributions Bar Chart
    ax1 = fig.add_subplot(gs[0, 0])
    contributors = list(contributors_total.keys())
    commits = list(contributors_total.values())

    # Use a professional color gradient
    cmap = plt.colormaps["viridis"]
    colors = [cmap(i / len(contributors)) for i in range(len(contributors))]

    # Limit to top 15 contributors for readability
    if len(contributors) > 15:
        contributors = contributors[:15]
        commits = commits[:15]
        colors = colors[:15]

    bars = ax1.bar(
        contributors, commits, color=colors, edgecolor="#2c3e50", linewidth=1.5
    )
    ax1.set_title(
        "Total Commits by Contributor",
        fontweight="bold",
        fontsize=16,
        color="#2c3e50",
        pad=20,
    )
    ax1.set_ylabel("Number of Commits", fontsize=12, color="#34495e")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # Improve x-axis labels for better readability
    ax1.tick_params(axis="x", rotation=45, labelsize=8)
    # Adjust spacing between labels to prevent overlap
    if len(contributors) > 8:
        ax1.tick_params(axis="x", which="major", pad=10)

    # For contributors with very few commits, use shorter names or abbreviations
    new_labels = []
    for i, (contributor, commit_count) in enumerate(zip(contributors, commits)):
        if (
            commit_count < 10 and len(contributor) > 15
        ):  # Small contributors with long names
            # Use first name + last initial
            parts = contributor.split()
            if len(parts) >= 2:
                short_name = f"{parts[0]} {parts[-1][0]}."
                new_labels.append(short_name)
            else:
                new_labels.append(
                    contributor[:12] + "..." if len(contributor) > 12 else contributor
                )
        else:
            new_labels.append(contributor)
    # Set the x-tick labels properly to avoid warning
    ax1.set_xticks(range(len(new_labels)))
    ax1.set_xticklabels(new_labels)

    # Add value labels on bars
    for bar, value in zip(bars, commits):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(commits) * 0.01,
            str(value),
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=9,
        )

    # 2. Pie Chart of Contributions (top contributors only)
    ax2 = fig.add_subplot(gs[0, 1])
    # Group smaller contributors together
    main_contributors = dict(list(contributors_total.items())[:8])  # Top 8
    others_count = (
        sum(list(contributors_total.values())[8:]) if len(contributors_total) > 8 else 0
    )
    if others_count > 0:
        main_contributors["Others"] = others_count

    if main_contributors:
        # Use better colors for pie chart with good contrast
        pie_colors = plt.cm.Set2(np.linspace(0, 1, len(main_contributors)))

        # Create pie chart without labels and without percentage text
        wedges, texts, autotexts = ax2.pie(
            main_contributors.values(),
            labels=None,  # Remove labels from pie chart
            autopct="",  # No percentage text in the pie
            startangle=90,
            colors=pie_colors,
            explode=[
                0.05 if i == 0 else 0 for i in range(len(main_contributors))
            ],  # Slightly explode the largest slice
            shadow=True,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        ax2.set_title(
            "Contribution Distribution",
            fontweight="bold",
            fontsize=16,
            color="#2c3e50",
            pad=20,
        )

        # Calculate percentages for legend
        total_value = sum(main_contributors.values())
        legend_labels = []
        for name, value in main_contributors.items():
            percentage = (value / total_value) * 100
            legend_labels.append(f"{name} ({percentage:.1f}%)")

        # Add a clean legend box with each name and percentage on its own line
        ax2.legend(
            wedges,
            legend_labels,
            title="Contributors",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=10,
            title_fontsize=11,
            frameon=True,
            fancybox=True,
            shadow=True,
        )

    # 3. Monthly Activity Heatmap
    ax3 = fig.add_subplot(gs[0, 2])

    # Get months that have activity
    active_months = set()
    for (contributor, month), count in monthly_data.items():
        active_months.add(month)

    if active_months:
        # Filter out future months if analyzing current year OR all-time
        current_date = datetime.now()
        if (year is None) or (int(year) == current_date.year):
            # Only show months up to current month
            months = sorted([m for m in active_months if m <= current_date.month])
        else:
            months = sorted(active_months)
        top_contributors = list(contributors_total.keys())[:6]  # Top 6 for heatmap

        activity_matrix = []
        for contributor in top_contributors:
            monthly_commits = []
            for month in months:
                commits = monthly_data.get((contributor, month), 0)
                monthly_commits.append(commits)
            activity_matrix.append(monthly_commits)

        if activity_matrix and months:
            im = ax3.imshow(
                activity_matrix, cmap="coolwarm", aspect="auto", interpolation="nearest"
            )
            ax3.set_xticks(range(len(months)))
            month_names = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            ax3.set_xticklabels([month_names[m - 1] for m in months])
            ax3.set_yticks(range(len(top_contributors)))
            ax3.set_yticklabels(top_contributors)
            ax3.set_title(
                "Monthly Activity Heatmap",
                fontweight="bold",
                fontsize=16,
                color="#2c3e50",
                pad=20,
            )

            # Add text annotations
            for i in range(len(top_contributors)):
                for j in range(len(months)):
                    value = activity_matrix[i][j]
                    if value > 0:
                        ax3.text(
                            j,
                            i,
                            str(value),
                            ha="center",
                            va="center",
                            color=(
                                "white"
                                if value
                                > max(max(row) for row in activity_matrix) * 0.3
                                else "black"
                            ),
                            fontweight="bold",
                            fontsize=8,
                        )

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax3, shrink=0.8)
            cbar.set_label("Commits", rotation=270, labelpad=15)
    else:
        ax3.text(
            0.5,
            0.5,
            "No monthly data available",
            ha="center",
            va="center",
            transform=ax3.transAxes,
        )
        ax3.set_title("Monthly Activity Heatmap", fontweight="bold", fontsize=14)

    # 4. Monthly Timeline
    ax4 = fig.add_subplot(gs[1, 0])

    if active_months:
        # Calculate total commits per month
        monthly_totals = defaultdict(int)
        for (contributor, month), count in monthly_data.items():
            monthly_totals[month] += count

        # Filter out any future months if analyzing current year or all-time
        current_date = datetime.now()
        if (year is None) or (int(year) == current_date.year):
            # Only include months up to current month
            months_with_data = sorted(
                [m for m in monthly_totals.keys() if m <= current_date.month]
            )
        else:
            months_with_data = sorted(monthly_totals.keys())
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        if months_with_data:
            # Create gradient effect for the line plot
            ax4.plot(
                months_with_data,
                [monthly_totals[m] for m in months_with_data],
                marker="o",
                linewidth=3,
                markersize=10,
                color="#3498db",
                markerfacecolor="#e74c3c",
                markeredgewidth=2,
                markeredgecolor="#2c3e50",
            )
            ax4.fill_between(
                months_with_data,
                [monthly_totals[m] for m in months_with_data],
                alpha=0.2,
                color="#3498db",
            )
            ax4.set_title(
                "Monthly Commit Activity",
                fontweight="bold",
                fontsize=16,
                color="#2c3e50",
                pad=20,
            )
            ax4.spines["top"].set_visible(False)
            ax4.spines["right"].set_visible(False)
            ax4.set_xlabel("Month")
            ax4.set_ylabel("Total Commits")
            # FORCE matplotlib to use ONLY our specified ticks
            ax4.set_xticks(months_with_data)
            ax4.set_xticks(months_with_data, minor=False)  # No minor ticks
            ax4.set_xticklabels([month_names[m - 1] for m in months_with_data])
            ax4.xaxis.set_tick_params(
                which="minor", bottom=False, top=False
            )  # Disable minor ticks
            ax4.grid(True, alpha=0.3)

            # Add a subtle 'Today' marker within the current year for context
            if year and int(year) == current_date.year:
                days_in_month = calendar.monthrange(
                    current_date.year, current_date.month
                )[1]
                today_pos = current_date.month + (current_date.day - 1) / float(
                    days_in_month
                )
                if 1 <= today_pos <= 12:
                    ax4.axvline(
                        x=today_pos,
                        color="#7f8c8d",
                        linestyle=":",
                        linewidth=1.5,
                        alpha=0.7,
                    )
                    ax4.text(
                        today_pos,
                        max([monthly_totals[m] for m in months_with_data]) * 0.6,
                        "Today",
                        rotation=90,
                        va="bottom",
                        ha="center",
                        fontsize=10,
                        color="#7f8c8d",
                        fontweight="bold",
                    )

            # Ensure x-axis limits never go beyond the current month
            if year and int(year) == current_date.year:
                max_x = min(max(months_with_data), current_date.month)
                ax4.set_xlim(0.5, max_x + 0.5)
            else:
                ax4.set_xlim(min(months_with_data) - 0.5, max(months_with_data) + 0.5)

            # Add AI-boom marker if applicable
            if ai_boom_marker:
                # AI boom is in June (month 6), only show if we have June data
                if 6 in months_with_data:
                    ax4.axvline(
                        x=ai_boom_marker,
                        color="red",
                        linestyle="--",
                        alpha=0.7,
                        linewidth=2,
                        label="AI-boom",
                    )
                    # Add text annotation
                    max_y = max(monthly_totals[m] for m in months_with_data)
                    ax4.text(
                        ai_boom_marker,
                        max_y * 0.8,
                        "AI-boom",
                        rotation=90,
                        verticalalignment="bottom",
                        horizontalalignment="center",
                        fontsize=14,
                        color="red",
                        fontweight="bold",
                    )

            # Add value labels on points
            for month in months_with_data:
                ax4.annotate(
                    str(monthly_totals[month]),
                    (month, monthly_totals[month]),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontweight="bold",
                    fontsize=8,
                )
    else:
        ax4.text(
            0.5,
            0.5,
            "No timeline data available",
            ha="center",
            va="center",
            transform=ax4.transAxes,
        )
        ax4.set_title("Monthly Commit Activity", fontweight="bold", fontsize=14)

    # 5. Top Contributors Timeline
    ax5 = fig.add_subplot(gs[1, 1])

    if active_months:
        top_3_contributors = list(contributors_total.keys())[:3]
        # Use distinctive colors with good contrast
        colors_line = ["#e74c3c", "#3498db", "#2ecc71"]

        # Filter out future months if analyzing current year
        current_date = datetime.now()
        if year and int(year) == current_date.year:
            max_month = current_date.month
        else:
            max_month = 12

        # Build valid months list (cap future months also for all-time)
        if (year is None) or (int(year) == current_date.year):
            valid_months = sorted([m for m in active_months if m <= current_date.month])
        else:
            valid_months = sorted(active_months)

        for idx, contributor in enumerate(top_3_contributors):
            contributor_months = []
            contributor_commits = []
            for month in valid_months:
                if (contributor, month) in monthly_data:
                    contributor_months.append(month)
                    contributor_commits.append(monthly_data[(contributor, month)])

            if contributor_months:
                ax5.plot(
                    contributor_months,
                    contributor_commits,
                    marker="o",
                    linewidth=2.5,
                    markersize=8,
                    label=contributor,
                    color=colors_line[idx % len(colors_line)],
                    alpha=0.8,
                    markeredgewidth=2,
                    markeredgecolor="#2c3e50",
                )

        ax5.set_title(
            "Top Contributors Monthly Activity",
            fontweight="bold",
            fontsize=16,
            color="#2c3e50",
            pad=20,
        )
        ax5.set_xlabel("Month")
        ax5.spines["top"].set_visible(False)
        ax5.spines["right"].set_visible(False)
        ax5.set_ylabel("Commits")
        # Only show months with actual activity (filtering out future months)
        if (year is None) or (int(year) == current_date.year):
            valid_months = sorted([m for m in active_months if m <= current_date.month])
        else:
            valid_months = sorted(active_months)

        # FORCE matplotlib to use ONLY these ticks, no auto-generation
        ax5.set_xticks(valid_months)
        ax5.set_xticks(valid_months, minor=False)  # Ensure no minor ticks
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        ax5.set_xticklabels([month_names[m - 1] for m in valid_months])
        ax5.xaxis.set_tick_params(
            which="minor", bottom=False, top=False
        )  # Disable minor ticks
        ax5.legend(fontsize=10)
        ax5.grid(True, alpha=0.3)

        # Set x-axis limits using the SAME valid_months variable
        # For current year, never go beyond the current month
        if valid_months:
            if year and int(year) == current_date.year:
                max_x = min(max(valid_months), current_date.month)
                ax5.set_xlim(0.5, max_x + 0.5)
            else:
                ax5.set_xlim(min(valid_months) - 0.5, max(valid_months) + 0.5)

        # Add a subtle 'Today' marker for context on current year
        if year and int(year) == current_date.year:
            days_in_month = calendar.monthrange(current_date.year, current_date.month)[
                1
            ]
            today_pos = current_date.month + (current_date.day - 1) / float(
                days_in_month
            )
            if valid_months and (min(valid_months) - 0.5) <= today_pos <= (
                max(valid_months) + 0.5
            ):
                ax5.axvline(
                    x=today_pos,
                    color="#7f8c8d",
                    linestyle=":",
                    linewidth=1.5,
                    alpha=0.7,
                )
                # Use the max commits across visible data for label height
                _max_y = 0
                for contributor in list(contributors_total.keys())[:3]:
                    for m in valid_months:
                        _max_y = max(_max_y, monthly_data.get((contributor, m), 0))
                if _max_y > 0:
                    ax5.text(
                        today_pos,
                        _max_y * 0.6,
                        "Today",
                        rotation=90,
                        va="bottom",
                        ha="center",
                        fontsize=10,
                        color="#7f8c8d",
                        fontweight="bold",
                    )

        # Add AI-boom marker if applicable
        if ai_boom_marker:
            # AI boom is in June (month 6), only show if we have June data
            if 6 in active_months:
                ax5.axvline(
                    x=ai_boom_marker,
                    color="red",
                    linestyle="--",
                    alpha=0.7,
                    linewidth=2,
                )
                # Add text annotation
                # Find the maximum y-value across all contributors
                max_commits = 0
                for contributor in list(contributors_total.keys())[:3]:
                    for month in sorted(active_months):
                        if (contributor, month) in monthly_data:
                            max_commits = max(
                                max_commits, monthly_data[(contributor, month)]
                            )

                if max_commits > 0:
                    ax5.text(
                        ai_boom_marker,
                        max_commits * 0.8,
                        "AI-boom",
                        rotation=90,
                        verticalalignment="bottom",
                        horizontalalignment="center",
                        fontsize=14,
                        color="red",
                        fontweight="bold",
                    )
    else:
        ax5.text(
            0.5,
            0.5,
            "No contributor timeline data",
            ha="center",
            va="center",
            transform=ax5.transAxes,
        )
        ax5.set_title(
            "Top Contributors Monthly Activity", fontweight="bold", fontsize=14
        )

    # 6. Statistics Summary
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.axis("off")

    # Calculate stats
    total_contributors = len(contributors_total)
    avg_commits = total_commits / total_contributors if total_contributors > 0 else 0

    if active_months:
        monthly_totals = defaultdict(int)
        for (contributor, month), count in monthly_data.items():
            monthly_totals[month] += count
        # When viewing current year or all-time, ignore future months in stats too
        current_date = datetime.now()
        if (year is None) or (int(year) == current_date.year):
            filtered_totals = {
                m: v for m, v in monthly_totals.items() if m <= current_date.month
            }
        else:
            filtered_totals = dict(monthly_totals)
        most_active_month = (
            max(filtered_totals.items(), key=lambda x: x[1])
            if filtered_totals
            else None
        )
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        most_active_month_name = (
            month_names[most_active_month[0] - 1] if most_active_month else "N/A"
        )
        most_active_month_commits = most_active_month[1] if most_active_month else 0
        # Count active months within the considered range
        if (year is None) or (int(year) == current_date.year):
            active_months_count = len(
                set(m for (c, m) in monthly_data.keys() if m <= current_date.month)
            )
        else:
            active_months_count = len(set(m for (c, m) in monthly_data.keys()))
    else:
        most_active_month_name = "N/A"
        most_active_month_commits = 0
        active_months_count = 0

    top_contributor = (
        max(contributors_total.items(), key=lambda x: x[1])
        if contributors_total
        else ("N/A", 0)
    )

    generated_by_total = sum(generated_by_monthly.values())
    generated_by_percentage = (
        (generated_by_total / total_commits) * 100 if total_commits else 0
    )

    # Add note about date anomaly if we detect future dates
    current_year = datetime.now().year
    date_note = ""
    if year and int(year) > current_year:
        date_note = "\n⚠️ Note: System clock may be incorrect"

    stats_text = f"""kdevops Statistics {title_suffix}

Total Commits: {total_commits:,}
Total Contributors: {total_contributors}
Average Commits/Person: {avg_commits:.1f}

Most Active Month: {most_active_month_name}
({most_active_month_commits} commits)

Top Contributor: {top_contributor[0]}
({top_contributor[1]} commits)

Active Months: {active_months_count}

Generated-by Tag Commits: {generated_by_total} ({generated_by_percentage:.1f}% of total)

Project: Linux Kernel DevOps Framework
Analysis Period: {period_desc}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}{date_note}
"""

    ax6.text(
        0.1,
        0.9,
        stats_text,
        transform=ax6.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(
            boxstyle="round,pad=0.8",
            facecolor="#ecf0f1",
            edgecolor="#34495e",
            linewidth=2,
            alpha=0.9,
        ),
        color="#2c3e50",
    )

    # 7. Generated-by Tag Adoption Trend
    ax7 = fig.add_subplot(gs[2, :])
    if generated_by_monthly:
        timeline_map = {k: v for k, v in generated_by_monthly.items()}
        sorted_dates = sorted(timeline_map.keys())
        min_date = sorted_dates[0]
        max_date = sorted_dates[-1]
        date_range = pd.date_range(start=min_date, end=max_date, freq="MS")
        timeline_dates = [d.to_pydatetime() for d in date_range]
        timeline_counts = [timeline_map.get(d.date(), 0) for d in date_range]

        ax7.plot(
            timeline_dates,
            timeline_counts,
            marker="o",
            linewidth=3,
            markersize=8,
            color="#8e44ad",
            markerfacecolor="#f39c12",
            markeredgecolor="#2c3e50",
            markeredgewidth=1.2,
        )
        if len(timeline_dates) > 1:
            ax7.fill_between(
                timeline_dates,
                timeline_counts,
                alpha=0.15,
                color="#8e44ad",
            )

        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        ax7.xaxis.set_major_locator(locator)
        ax7.xaxis.set_major_formatter(formatter)

        ax7.set_title(
            "Generated-by Tag Adoption Over Time",
            fontweight="bold",
            fontsize=16,
            color="#2c3e50",
            pad=20,
        )
        ax7.set_ylabel("Commits with Generated-by", fontsize=12, color="#34495e")
        ax7.set_xlabel("Month", fontsize=12, color="#34495e")
        ax7.spines["top"].set_visible(False)
        ax7.spines["right"].set_visible(False)
        ax7.grid(True, alpha=0.3)
        ax7.set_ylim(bottom=0)
        ax7.tick_params(axis="x", labelrotation=45)

        ax7.text(
            0.01,
            0.95,
            f"Total commits tagged: {generated_by_total} ({generated_by_percentage:.1f}% of commits)",
            transform=ax7.transAxes,
            fontsize=10,
            fontweight="bold",
            color="#2c3e50",
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor="#f4ecf7",
                edgecolor="#8e44ad",
                linewidth=1.2,
                alpha=0.6,
            ),
            verticalalignment="top",
        )

        if (year is None) or (int(year) == datetime.now().year):
            current_marker = datetime.now()
            if (
                timeline_dates
                and timeline_dates[0] <= current_marker <= timeline_dates[-1]
            ):
                ax7.axvline(
                    current_marker,
                    color="#7f8c8d",
                    linestyle=":",
                    linewidth=1.2,
                    alpha=0.7,
                )
    else:
        ax7.set_title(
            "Generated-by Tag Adoption Over Time",
            fontweight="bold",
            fontsize=16,
            color="#2c3e50",
            pad=20,
        )
        ax7.spines["top"].set_visible(False)
        ax7.spines["right"].set_visible(False)
        ax7.set_ylabel("Commits with Generated-by", fontsize=12, color="#34495e")
        ax7.set_xlabel("Month", fontsize=12, color="#34495e")
        ax7.tick_params(axis="x", labelbottom=False)
        ax7.tick_params(axis="y", labelleft=False)
        ax7.set_ylim(0, 1)
        ax7.text(
            0.5,
            0.5,
            "No Generated-by tag usage detected",
            ha="center",
            va="center",
            transform=ax7.transAxes,
            fontsize=12,
            fontweight="bold",
            color="#7f8c8d",
        )

    fig.tight_layout(rect=[0, 0, 1, 0.97], pad=2.5)

    # Ensure output directory exists and save the plots
    os.makedirs("docs/contrib", exist_ok=True)
    png_file = f"docs/contrib/{output_base}.png"
    pdf_file = f"docs/contrib/{output_base}.pdf"

    plt.savefig(png_file, dpi=300, bbox_inches="tight", facecolor="#f8f9fa")
    plt.savefig(pdf_file, bbox_inches="tight", facecolor="#f8f9fa")

    print(f"✅ Contribution visualization saved as:")
    print(f"   - {png_file} (high-res image)")
    print(f"   - {pdf_file} (vector format)")

    return fig


def main():
    parser = argparse.ArgumentParser(
        description="Generate kdevops contribution visualization"
    )
    parser.add_argument(
        "--year",
        type=str,
        help="Year to analyze (e.g., 2025), if not specified analyzes all time",
    )
    parser.add_argument(
        "--month",
        type=str,
        help="Starting month to analyze (e.g., 04 for April), requires --year",
    )
    parser.add_argument(
        "--show", action="store_true", help="Display the graph after generation"
    )

    args = parser.parse_args()

    # Validate year if provided
    if args.year:
        try:
            year_int = int(args.year)
            current_year = datetime.now().year
            if year_int < 2005:  # Git was created in 2005
                print(
                    f"❌ Year {args.year} is too early. Git history starts around 2005."
                )
                sys.exit(1)
            if year_int > current_year:
                print(
                    f"❌ Year {args.year} is in the future. Current year is {current_year}."
                )
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid year format: {args.year}")
            sys.exit(1)

    # Validate month if provided
    if args.month:
        if not args.year:
            print("❌ Month parameter requires --year to be specified")
            sys.exit(1)
        try:
            month_int = int(args.month)
            if month_int < 1 or month_int > 12:
                print(f"❌ Invalid month: {args.month}. Must be between 01 and 12.")
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid month format: {args.month}")
            sys.exit(1)

    # Check if we're in a git repository
    try:
        run_git_command("git rev-parse --is-inside-work-tree")
    except:
        print("❌ This script must be run from within a git repository")
        sys.exit(1)

    print("🚀 Generating kdevops contribution visualization...")

    # Get contribution data
    month_int = int(args.month) if args.month else None
    (
        contributors_total,
        monthly_data,
        total_commits,
        period_desc,
        ai_boom_marker,
        generated_by_monthly,
    ) = get_contribution_data(args.year, month_int)

    # Create visualization
    fig = create_contribution_graphs(
        contributors_total,
        monthly_data,
        total_commits,
        period_desc,
        ai_boom_marker,
        generated_by_monthly,
        args.year,
        month_int,
    )

    if fig and args.show:
        plt.show()

    print("📈 Visualization complete!")


if __name__ == "__main__":
    main()
