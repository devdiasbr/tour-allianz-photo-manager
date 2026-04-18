import os
import unittest
import face_recognition
from PIL import Image
from app.services import face_service


class MobileImageRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session_path = os.path.join(os.getcwd(), "uploads", "270220262000")
        cls.problematic = [
            "IMG-20260227-WA0059.jpeg",
            "IMG_20260214_135246047_HDR.jpg",
            "IMG_20260214_135301354_HDR.jpg",
            "IMG_20260214_160357957_HDR.jpg",
        ]
        cls.reference_file = os.path.join(cls.session_path, "photo-1772231725334-4dh18y.jpg")
        ref_rgb, _ = face_service.load_image_rgb_with_metadata(cls.reference_file)
        ref_locs = face_recognition.face_locations(ref_rgb, number_of_times_to_upsample=1, model=face_service.FACE_DETECTION_MODEL)
        ref_encs = face_recognition.face_encodings(ref_rgb, ref_locs)
        if not ref_encs:
            raise RuntimeError("Referência sem rosto detectado")
        cls.reference_encodings = [ref_encs[0]]

    def test_problematic_images_have_mobile_exif_orientation(self):
        expected = {6, 8}
        for name in self.problematic:
            path = os.path.join(self.session_path, name)
            with Image.open(path) as img:
                exif = img.getexif()
            self.assertIn(exif.get(274), expected, msg=name)

    def test_exif_transpose_makes_detector_find_faces(self):
        for name in self.problematic:
            path = os.path.join(self.session_path, name)
            raw = face_recognition.load_image_file(path)
            raw_faces = face_recognition.face_locations(
                raw,
                number_of_times_to_upsample=1,
                model=face_service.FACE_DETECTION_MODEL,
            )
            fixed_rgb, _ = face_service.load_image_rgb_with_metadata(path)
            fixed_faces = face_recognition.face_locations(
                fixed_rgb,
                number_of_times_to_upsample=1,
                model=face_service.FACE_DETECTION_MODEL,
            )
            self.assertEqual(len(raw_faces), 0, msg=f"raw {name}")
            self.assertGreaterEqual(len(fixed_faces), 1, msg=f"fixed {name}")

    def test_scan_session_matches_all_problematic_images(self):
        results = face_service.scan_session(
            self.session_path,
            self.reference_encodings,
            tolerance=face_service.FACE_TOLERANCE,
        )
        matched = {os.path.basename(r.file_path) for r in results}
        for name in self.problematic:
            self.assertIn(name, matched, msg=name)


if __name__ == "__main__":
    unittest.main()
