#!/usr/bin/env python
"""Draw a simple diagram that explains how river distance is computed for one H3 cell."""

import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "figures")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "river_distance_diagram.png")


def add_box(ax, xy, width, height, text, facecolor, edgecolor="#222222"):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.5,
        facecolor=facecolor,
        edgecolor=edgecolor,
    )
    ax.add_patch(box)
    x, y = xy
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#111111",
        wrap=True,
    )


def add_arrow(ax, start, end):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="->",
        mutation_scale=18,
        linewidth=1.8,
        color="#333333",
    )
    ax.add_patch(arrow)


def main():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis("off")

    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    ax.text(
        6,
        9.5,
        "Quy trình tìm khoảng cách từ 1 ô H3 tới sông",
        ha="center",
        va="center",
        fontsize=18,
        fontweight="bold",
        color="#102542",
    )

    add_box(
        ax,
        (0.8, 7.2),
        2.6,
        1.1,
        "1. Ô H3\nLấy centroid của polygon",
        "#d8f3dc",
    )
    add_box(
        ax,
        (3.9, 7.2),
        2.8,
        1.1,
        "2. Raster sông\nĐọc River_DBSCL.tif",
        "#d0ebff",
    )
    add_box(
        ax,
        (7.1, 7.2),
        2.8,
        1.1,
        "3. Pixel sông\nTạo mask data == 1",
        "#ffe8cc",
    )
    add_box(
        ax,
        (10.2, 7.2),
        1.0,
        1.1,
        "",
        "#ffffff",
    )

    add_box(
        ax,
        (2.1, 4.9),
        2.9,
        1.2,
        "4. Tạo tọa độ pixel sông\n(rasterio.transform.xy)",
        "#e9d8fd",
    )
    add_box(
        ax,
        (6.0, 4.9),
        2.9,
        1.2,
        "5. Xây KDTree\nTìm điểm sông gần nhất",
        "#f8d7da",
    )
    add_box(
        ax,
        (9.0, 4.9),
        2.2,
        1.2,
        "6. Query centroid H3\nLấy khoảng cách gần nhất",
        "#fff3bf",
    )

    add_box(
        ax,
        (2.0, 2.0),
        3.4,
        1.2,
        "7. Quy đổi sang km\nNếu CRS địa lý: d * 111.32",
        "#f1f3f5",
    )
    add_box(
        ax,
        (6.2, 2.0),
        3.8,
        1.2,
        "8. Nếu ô có nước\nÉp khoảng cách = 0",
        "#d3f9d8",
    )
    add_box(
        ax,
        (10.4, 2.0),
        1.0,
        1.2,
        "",
        "#ffffff",
    )

    ax.text(
        6,
        0.7,
        "Output: river_proximity (km) + river_proximity_fraction",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#102542",
    )

    add_arrow(ax, (3.4, 7.75), (3.9, 7.75))
    add_arrow(ax, (6.7, 7.75), (7.1, 7.75))
    add_arrow(ax, (8.95, 7.2), (8.95, 6.15))
    add_arrow(ax, (3.5, 6.1), (6.0, 5.55))
    add_arrow(ax, (8.9, 5.55), (9.0, 5.55))
    add_arrow(ax, (10.1, 5.55), (10.1, 3.2))
    add_arrow(ax, (3.7, 3.2), (6.2, 3.2))
    add_arrow(ax, (10.0, 3.2), (10.0, 3.2))

    # Decorative notes
    ax.text(
        6,
        8.55,
        "Ý tưởng chính: centroid H3 -> pixel sông gần nhất -> khoảng cách",
        ha="center",
        va="center",
        fontsize=11,
        color="#555555",
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=200, bbox_inches="tight")
    print(f"✅ Đã lưu ảnh: {OUTPUT_PATH}")
    plt.show()


if __name__ == "__main__":
    main()
