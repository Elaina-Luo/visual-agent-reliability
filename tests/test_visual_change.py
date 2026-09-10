import unittest

from PIL import Image

from src.visual_change import changed_pixel_fraction, fuse_verification


class VisualChangeTests(unittest.TestCase):
    def test_identical_images_have_zero_change(self):
        image = Image.new("RGB", (100, 100), "white")
        self.assertEqual(changed_pixel_fraction(image, image.copy()), 0.0)

    def test_changed_region_has_expected_fraction(self):
        before = Image.new("RGB", (100, 100), "white")
        after = before.copy()
        for x in range(10):
            for y in range(10):
                after.putpixel((x, y), (0, 0, 0))

        self.assertAlmostEqual(
            changed_pixel_fraction(before, after),
            0.01,
        )

    def test_complete_semantics_take_precedence(self):
        self.assertEqual(fuse_verification("complete", 0.0), "complete")

    def test_pixels_override_false_no_effect(self):
        self.assertEqual(fuse_verification("no_effect", 0.01), "changed")

    def test_no_pixels_override_false_changed(self):
        self.assertEqual(fuse_verification("changed", 0.0), "no_effect")


if __name__ == "__main__":
    unittest.main()
