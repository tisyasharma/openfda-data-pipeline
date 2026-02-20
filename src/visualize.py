import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from adverse_event_api import AdverseEventAPI
from config import BASE_DIR


def plot_route_death_rates(results: list[dict], output_path: str) -> None:
    """Horizontal bar chart comparing death rates across drug administration routes."""
    routes = [r["_id"].title() for r in results]
    death_rates = [r["death_rate"] for r in results]
    totals = [r["total"] for r in results]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(routes, death_rates, color="crimson", alpha=0.85)

    for bar, total in zip(bars, totals):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"n={total}",
            va="center",
            fontsize=9,
            color="#555",
        )

    ax.set_xlabel("Death Rate (%)")
    ax.set_title(
        "Death Rate in FDA Drug Safety Reports by Administration Route",
        fontsize=13,
    )
    ax.invert_yaxis()
    # pad the x-axis so bar labels don't get clipped
    if death_rates:
        ax.set_xlim(right=max(death_rates) * 1.15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved chart to {output_path}")


def main():
    api = AdverseEventAPI()
    try:
        results = api.get_death_rate_by_route(min_reports=20)
        output_path = os.path.join(BASE_DIR, "route_death_rates.png")
        plot_route_death_rates(results, output_path)
    finally:
        api.close()


if __name__ == "__main__":
    main()
