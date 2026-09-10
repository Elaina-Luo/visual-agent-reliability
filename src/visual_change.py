from PIL import ImageChops


DEFAULT_INTENSITY_THRESHOLD = 8
DEFAULT_CHANGED_FRACTION_THRESHOLD = 0.0001


def changed_pixel_fraction(
    before_image,
    after_image,
    intensity_threshold=DEFAULT_INTENSITY_THRESHOLD,
):
    if before_image.size != after_image.size:
        raise ValueError("Before and after screenshots must have equal sizes.")

    difference = ImageChops.difference(
        before_image.convert("RGB"),
        after_image.convert("RGB"),
    )
    red, green, blue = difference.split()
    maximum_channel_difference = ImageChops.lighter(
        ImageChops.lighter(red, green),
        blue,
    )
    histogram = maximum_channel_difference.histogram()
    changed_pixels = sum(histogram[intensity_threshold:])
    total_pixels = before_image.width * before_image.height
    return changed_pixels / total_pixels


def fuse_verification(
    vlm_status,
    pixel_change_fraction,
    changed_fraction_threshold=DEFAULT_CHANGED_FRACTION_THRESHOLD,
):
    """Combine deterministic visual change with semantic VLM completion."""
    if vlm_status == "complete":
        return "complete"
    if pixel_change_fraction >= changed_fraction_threshold:
        return "changed"
    return "no_effect"
