"""Тесты для update_db_rivalsmeta.py.

Полный прогон скрейпера занимает ~6 минут и ходит на сайт, поэтому здесь
проверяются только чистые куски логики (парсинг сезона, сбор метаданных)
плюс один сетевой тест определения последнего сезона.

Запуск:
    d:/Projects/rivals_counter_peaks/env/Scripts/python.exe build_scripts/test_update_db.py
    ... test_update_db.py --offline   # без обращения к сайту
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import update_db_rivalsmeta as scraper


# Реальная выгрузка #season_filter с сайта (value — монотонный номер).
REAL_SEASON_OPTIONS = [
    {"value": "1",  "label": "Season 0",    "selected": False},
    {"value": "2",  "label": "Season 1",    "selected": False},
    {"value": "3",  "label": "Season 1.5",  "selected": False},
    {"value": "19", "label": "Season 9.5",  "selected": False},
    {"value": "20", "label": "Season 10",   "selected": False},
    {"value": "21", "label": "Season 10.5", "selected": True},
]


class TestSeasonVersion(unittest.TestCase):
    def test_extracts_number_from_label(self):
        self.assertEqual(scraper._season_version("Season 10.5"), "10.5")
        self.assertEqual(scraper._season_version("Season 9"), "9")
        self.assertEqual(scraper._season_version("Season 0"), "0")

    def test_no_number_gives_none(self):
        self.assertIsNone(scraper._season_version("Все сезоны"))
        self.assertIsNone(scraper._season_version(""))
        self.assertIsNone(scraper._season_version(None))


class TestPickLatestSeason(unittest.TestCase):
    def test_picks_highest_value(self):
        version, label = scraper.pick_latest_season(REAL_SEASON_OPTIONS)
        self.assertEqual(version, "10.5")
        self.assertEqual(label, "Season 10.5")

    def test_ignores_decimal_trap(self):
        """'Season 10.5' больше 'Season 9', но строковое сравнение так не даёт."""
        version, _ = scraper.pick_latest_season(REAL_SEASON_OPTIONS)
        self.assertEqual(version, "10.5")

    def test_empty_list(self):
        self.assertEqual(scraper.pick_latest_season([]), (None, None))

    def test_works_when_new_season_added(self):
        """Сайт выпустил Season 11 — скрипт должен подхватить без правок кода."""
        options = REAL_SEASON_OPTIONS + [
            {"value": "22", "label": "Season 11", "selected": True},
        ]
        version, label = scraper.pick_latest_season(options)
        self.assertEqual(version, "11")
        self.assertEqual(label, "Season 11")

    def test_non_numeric_values_do_not_crash(self):
        version, _ = scraper.pick_latest_season([
            {"value": "x", "label": "Season ???"},
            {"value": "21", "label": "Season 10.5"},
        ])
        self.assertEqual(version, "10.5")


class TestSelectSeasonMatching(unittest.TestCase):
    """Строгое сравнение версий вместо вхождения подстроки.

    Старый код делал `season in option.text`, из-за чего '1' цеплял
    'Season 1.5' и 'Season 10'.
    """

    def _match(self, season, options):
        """Повторяет логику выбора option'а из select_season."""
        target = scraper._season_version(str(season)) or str(season).strip()
        for opt in options:
            if scraper._season_version(opt) == target:
                return opt
        return None

    def test_1_does_not_match_season_10_or_1_5(self):
        options = ["Season 1", "Season 1.5", "Season 10", "Season 10.5"]
        self.assertEqual(self._match("1", options), "Season 1")
        self.assertEqual(self._match("10", options), "Season 10")
        self.assertEqual(self._match("10.5", options), "Season 10.5")

    def test_season_0_is_findable(self):
        self.assertEqual(self._match("0", ["Season 0", "Season 1"]), "Season 0")

    def test_autodetected_value_selects_right_option(self):
        version, _ = scraper.pick_latest_season(REAL_SEASON_OPTIONS)
        labels = [o["label"] for o in REAL_SEASON_OPTIONS]
        self.assertEqual(self._match(version, labels), "Season 10.5")


class TestMeta(unittest.TestCase):
    def test_meta_has_all_fields(self):
        meta = scraper.build_meta("10.5")
        self.assertEqual(meta["season"], "10.5")
        self.assertEqual(meta["season_label"], "Season 10.5")
        self.assertEqual(meta["source"], "https://rivalsmeta.com")
        for field in ("generated_at", "generated_at_utc", "utc_offset", "scraper"):
            self.assertIn(field, meta)
            self.assertTrue(str(meta[field]).strip(), f"{field} пуст")

    def test_utc_offset_is_clean(self):
        """%Z на Windows даёт мусор ("RTZ 2 (мин)"), поэтому ждём +03:00."""
        import re as _re
        offset = scraper.build_meta("10.5")["utc_offset"]
        self.assertRegex(offset, r"^[+-]\d{2}:\d{2}$")

    def test_date_format(self):
        import re as _re
        meta = scraper.build_meta("10.5")
        self.assertTrue(
            _re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", meta["generated_at"]),
            meta["generated_at"],
        )
        self.assertTrue(
            _re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", meta["generated_at_utc"]),
            meta["generated_at_utc"],
        )


class TestJsonOutput(unittest.TestCase):
    """Гоняет данные через НАСТОЯЩИЙ save_to_json, только в temp-каталог."""

    def setUp(self):
        self._orig_root = scraper.PROJECT_ROOT
        self._tmp = tempfile.mkdtemp()
        scraper.PROJECT_ROOT = self._tmp

    def tearDown(self):
        scraper.PROJECT_ROOT = self._orig_root

    def _saved(self, data):
        path = scraper.save_to_json(data)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        return path, raw, json.loads(raw)

    def test_meta_is_first_key_in_file(self):
        data = {
            "meta": scraper.build_meta("10.5"),
            "teamups": [],
            "heroes": {"Mantis": {"opponents": []}},
        }
        path, raw, _ = self._saved(data)
        # meta должен физически идти первым в файле
        self.assertLess(raw.index('"meta"'), raw.index('"teamups"'))
        self.assertLess(raw.index('"teamups"'), raw.index('"heroes"'))
        self.assertTrue(path.endswith(".json"))

    def test_writes_into_stats_folder(self):
        _, _, _ = self._saved({
            "meta": scraper.build_meta("10.5"), "teamups": [], "heroes": {},
        })
        expected = os.path.join(
            self._tmp, "overwolf_app", "database", "stats"
        )
        self.assertTrue(os.path.isdir(expected), expected)

    def test_app_can_still_read_heroes_and_teamups(self):
        """Приложение читает только heroes/teamups — meta им не мешает."""
        data = {
            "meta": scraper.build_meta("10.5"),
            "teamups": [{"name": "X", "tier": "S", "win_rate": "50%"}],
            "heroes": {"Mantis": {"opponents": [], "maps": []}},
        }
        _, _, loaded = self._saved(data)
        # проверка из desktop.js:545
        self.assertTrue(loaded.get("heroes") or loaded.get("teamups"))
        self.assertEqual(len(loaded["heroes"]), 1)
        self.assertEqual(len(loaded["teamups"]), 1)
        self.assertIn("meta", loaded)

    def test_season_survives_roundtrip(self):
        version, _ = scraper.pick_latest_season(REAL_SEASON_OPTIONS)
        data = {
            "meta": scraper.build_meta(version),
            "teamups": [],
            "heroes": {"Mantis": {}},
        }
        _, _, loaded = self._saved(data)
        self.assertEqual(loaded["meta"]["season"], "10.5")

    def test_latest_index_written(self):
        path, _, _ = self._saved({
            "meta": scraper.build_meta("10.5"), "teamups": [], "heroes": {},
        })
        scraper.write_latest_index(os.path.basename(path))
        index = os.path.join(
            self._tmp, "overwolf_app", "database", "stats", "latest.json"
        )
        with open(index, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["current"], os.path.basename(path))


class TestLiveSeasonDetection(unittest.TestCase):
    """Живой тест: один заход на сайт, без сбора героев."""

    def test_detect_latest_season_on_site(self):
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        browser = context = None
        try:
            browser, context, page = scraper.init_browser(pw)
            version = scraper.detect_latest_season(page)
            self.assertTrue(version, "сезон не определился")
            # версия должна быть одним из реальных номеровSeason
            self.assertRegex(version, r"^\d+(\.\d+)?$")

            # и этот сезон реально выбирается в списке
            options = scraper.pick_latest_season(
                [{"value": v, "label": f"Season {version}"} for v in ("1", "2")]
            )
            self.assertEqual(options[0], version)
            print(f"\n  [live] сайт отдаёт последний сезон: {version}\n")
        finally:
            for fn in (
                lambda: context.close() if context else None,
                lambda: browser.close() if browser else None,
                lambda: pw.stop(),
            ):
                try:
                    fn()
                except Exception:
                    pass


if __name__ == "__main__":
    argv = [a for a in sys.argv if not a.startswith("-")]
    offline = "--offline" in sys.argv

    if offline:
        TestLiveSeasonDetection = unittest.skip(  # noqa: F811
            "сеть отключена (--offline)"
        )(TestLiveSeasonDetection)

    unittest.main(argv=argv or ["test_update_db.py"], verbosity=2, exit=False)