import unittest
from classifier import classify

class ClassificationTests(unittest.TestCase):
    def test_platforms(self):
        cases = {
            "Nintendo Game Boy Advance SP AGS-001": "Game Boy Advance",
            "Pokemon Oro Game Boy Color": "Game Boy Color",
            "Nintendo Switch OLED console": "Nintendo Switch",
            "Nintendo Switch 2 console": "Nintendo Switch 2",
            "Nintendo DS Lite rosa": "Nintendo DS",
            "Nintendo 3DS XL": "Nintendo 3DS",
            "Sony PlayStation 2 slim": "PlayStation 2",
            "Sony PS Vita": "PS Vita",
            "Microsoft Xbox Series X": "Xbox Series",
            "Sega Mega Drive 2": "Sega Mega Drive",
            "Videogioco vintage": "Altri / da classificare",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(classify(title), expected)

if __name__ == "__main__":
    unittest.main()
