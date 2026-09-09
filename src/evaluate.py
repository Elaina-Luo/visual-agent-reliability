def point_in_bbox(point, bbox):
    """
    Check whether a predicted click point is inside a target bounding box.

    Args:
        point: [x, y]
        bbox: [x1, y1, x2, y2]

    Returns:
        True if the point is inside or on the bbox boundary.
    """
    x, y = point
    x1, y1, x2, y2 = bbox

    return x1 <= x <= x2 and y1 <= y <= y2


def main():
    bbox = [
        0.9479166666666666,
        0.14444444444444443,
        0.99375,
        0.2074074074074074,
    ]

    inside_point = [0.97, 0.17]
    outside_point = [0.50, 0.50]
    boundary_point = [bbox[0], bbox[1]]

    assert point_in_bbox(inside_point, bbox) is True
    assert point_in_bbox(outside_point, bbox) is False
    assert point_in_bbox(boundary_point, bbox) is True

    print("Inside point: PASS")
    print("Outside point: PASS")
    print("Boundary point: PASS")
    print("All evaluator checks passed")


if __name__ == "__main__":
    main()