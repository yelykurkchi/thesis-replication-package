# ethical_testing/generate_restricted_yaml.py

import os
import yaml
from ethical_testing.config.waypoints import area_map_waypoints, waypoints


def main():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir, "config")
    os.makedirs(config_dir, exist_ok=True)
    output_path = os.path.join(config_dir, "restricted_areas.yaml")

    restricted_areas = ["Area 3", "Area 4"]
    #restricted_areas = ["Area 4"] 
    yaml_data = {"restricted_areas": []}

    for area in restricted_areas:
        wp_names = area_map_waypoints[area]

        xs = [waypoints[name]["x"] for name in wp_names]
        ys = [waypoints[name]["y"] for name in wp_names]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        polygon = [
            [min_x, min_y],  # bottom-left
            [min_x, max_y],  # top-left
            [max_x, max_y],  # top-right
            [max_x, min_y],  # bottom-right
        ]

        yaml_data["restricted_areas"].append({
            "name": area,
            "polygon": polygon
        })


    with open(output_path, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False)

    print(f"\nGenerated restricted_areas.yaml at:")
    print(f"  {output_path}\n")


if __name__ == "__main__":
    main()