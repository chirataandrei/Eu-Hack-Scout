import unittest
from datetime import date, timedelta

from euhackscout.delivery.emailer import build_email, split_for_email
from euhackscout.models import Format, Hackathon


def _h(**kwargs) -> Hackathon:
    defaults = dict(
        name="HackITAll",
        organizer="LSAC",
        url="https://hack.lsacbucuresti.ro/",
        source="lsac",
        location="Bucharest, Romania",
        format=Format.IN_PERSON,
        start_date=date.today() + timedelta(days=20),
        registration_deadline=date.today() + timedelta(days=3),
    )
    defaults.update(kwargs)
    return Hackathon(**defaults)


class EmailTests(unittest.TestCase):
    def test_section_order_and_deadline(self) -> None:
        buc = _h()
        eur = _h(
            name="Junction",
            organizer="Junction",
            url="https://hackjunction.com/",
            location="Helsinki, Finland",
            registration_deadline=date.today() + timedelta(days=40),
        )
        onl = _h(
            name="Shipaton",
            organizer="RevenueCat",
            url="https://devpost.com/shipaton",
            location="Online",
            format=Format.ONLINE,
            registration_deadline=date.today() + timedelta(days=40),
        )
        bucharest, europe, online = split_for_email([eur, onl, buc])
        self.assertEqual([h.name for h in bucharest], ["HackITAll"])
        self.assertEqual([h.name for h in europe], ["Junction"])
        self.assertEqual([h.name for h in online], ["Shipaton"])

        subject, plain, html_body = build_email([buc, eur, onl], [buc, eur, onl])
        self.assertIn("3 new", subject)
        self.assertLess(plain.find("HackITAll"), plain.find("Junction"))
        self.assertLess(plain.find("Junction"), plain.find("Shipaton"))
        self.assertIn("Deadline:", plain)
        self.assertIn("HackITAll", html_body)
        self.assertIn("Deadline:", html_body)
        self.assertIn("TOP PRIORITATE", html_body)

    def test_empty(self) -> None:
        subject, plain, html_body = build_email([], [])
        self.assertIn("0 new", subject)
        self.assertIn("Nimic nou", plain)
        self.assertIn("Nimic nou", html_body)


if __name__ == "__main__":
    unittest.main()
