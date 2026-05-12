import json
import math
from typing import Dict, Iterable, List, Tuple, Union


def as_polygon_coords(
    n_as: int,
    radius: float = 200.0,
    center: Tuple[float, float] = (0.0, 0.0),
    start_angle_deg: float = -90.0,
) -> List[Dict[str, int]]:
    """
    Return coordinates for AS positions on a regular polygon.
    """
    if n_as <= 0:
        raise ValueError("n_as must be >= 1")

    cx, cy = center
    coords: List[Dict[str, int]] = []

    for i in range(n_as):
        angle = math.radians(start_angle_deg + (360.0 / n_as) * i)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        coords.append({"index": i + 1, "x": int(round(x)), "y": int(round(y))})

    return coords


def as_coords_from_intent(
    intent_or_path: Union[str, Dict],
    radius: float = 200.0,
    center: Tuple[float, float] = (0.0, 0.0),
    start_angle_deg: float = -90.0,
) -> Dict[int, Dict[str, int]]:
    """
    Return a dict mapping AS number -> {x, y} from an intent file or dict.
    """
    if isinstance(intent_or_path, str):
        with open(intent_or_path, "r", encoding="utf-8") as f:
            intent = json.load(f)
    else:
        intent = intent_or_path

    as_list: Iterable = intent.get("as", [])
    if not as_list:
        return {}

    coords = as_polygon_coords(
        n_as=len(as_list),
        radius=radius,
        center=center,
        start_angle_deg=start_angle_deg,
    )

    result: Dict[int, Dict[str, int]] = {}
    for i, as_item in enumerate(as_list):
        as_nb = int(as_item.get("nb", i + 1))
        result[as_nb] = {"x": coords[i]["x"], "y": coords[i]["y"]}

    return result


def router_coords_from_intent(
    intent_or_path: Union[str, Dict],
    as_radius: float = 200.0,
    router_radius: float = 60.0,
    center: Tuple[float, float] = (0.0, 0.0),
    as_start_angle_deg: float = -90.0,
    router_start_angle_deg: float = -90.0,
) -> Dict[str, Dict[str, int]]:
    """
    Return router coordinates placed on small polygons around each AS center.
    """
    if isinstance(intent_or_path, str):
        with open(intent_or_path, "r", encoding="utf-8") as f:
            intent = json.load(f)
    else:
        intent = intent_or_path

    as_positions = as_coords_from_intent(
        intent,
        radius=as_radius,
        center=center,
        start_angle_deg=as_start_angle_deg,
    )

    routers_by_as: Dict[int, List[str]] = {}
    for router in intent.get("routers", []):
        as_nb = int(router.get("asn"))
        routers_by_as.setdefault(as_nb, []).append(router.get("name"))

    result: Dict[str, Dict[str, int]] = {}

    for as_nb, router_names in routers_by_as.items():
        if as_nb not in as_positions:
            continue

        as_x = as_positions[as_nb]["x"]
        as_y = as_positions[as_nb]["y"]

        if len(router_names) == 1:
            coords = [{"x": as_x, "y": as_y}]
        else:
            coords = as_polygon_coords(
                n_as=len(router_names),
                radius=router_radius,
                center=(as_x, as_y),
                start_angle_deg=router_start_angle_deg,
            )

        for i, router_name in enumerate(router_names):
            x = coords[i]["x"]
            y = coords[i]["y"]
            result[router_name] = {"x": int(round(x)), "y": int(round(y))}

    return result
