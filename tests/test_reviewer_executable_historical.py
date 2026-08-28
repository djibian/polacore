import os
import unittest

from scripts import reviewer_executable_historical as historical


RATIONALE = "Exercise one bounded historical behavior without receiving repair metadata."
SUPPORT = {
    "merge_governor.py": b"VALUE = 7\n",
    "merge_provider_capability.py": b"CAPABILITY = 'bounded'\n",
}


def challenge(code: str, name: str = "challenge_historical_case") -> dict[str, str]:
    return {
        "schema": historical.base.SCHEMA,
        "name": name,
        "rationale": RATIONALE,
        "code": code,
    }


class HistoricalChallengeContractTest(unittest.TestCase):
    def test_plain_public_candidate_api_is_allowed(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_public(self):
        self.assertEqual(candidate.public_value(), 3)
""")
        historical.validate_historical_challenge(value)

    def test_exact_sys_argv_hook_is_allowed(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_argv(self):
        candidate.sys.argv = ["collector", "--output", "result.json"]
        self.assertEqual(candidate.argv_value(), "result.json")
""")
        result = historical.run_control(
            value,
            b"import sys\ndef argv_value():\n    return sys.argv[-1]\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_exact_os_environ_hook_is_allowed_and_parent_secret_is_scrubbed(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_env(self):
        self.assertIsNone(candidate.os.environ.get("ALBERT_API_KEY"))
        candidate.os.environ["GITHUB_TOKEN"] = "synthetic-only"
        self.assertEqual(candidate.token_value(), "synthetic-only")
""")
        previous = os.environ.get("ALBERT_API_KEY")
        os.environ["ALBERT_API_KEY"] = "must-not-cross"
        try:
            result = historical.run_control(
                value,
                b"import os\ndef token_value():\n    return os.environ.get('GITHUB_TOKEN')\n",
                SUPPORT,
                candidate_sha="control",
            )
        finally:
            if previous is None:
                os.environ.pop("ALBERT_API_KEY", None)
            else:
                os.environ["ALBERT_API_KEY"] = previous
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_exact_build_opener_hook_is_allowed(self):
        value = challenge("""import candidate
import unittest

calls = []
def fake_build_opener(*handlers):
    calls.append(len(handlers))
    return object()

class CandidateTest(unittest.TestCase):
    def test_opener(self):
        candidate.urllib.request.build_opener = fake_build_opener
        candidate.make_opener()
        self.assertEqual(calls, [0])
""")
        result = historical.run_control(
            value,
            b"import urllib.request\ndef make_opener():\n    return urllib.request.build_opener()\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_sys_modules_escape_is_rejected(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        self.assertIn("os", candidate.sys.modules)
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_historical_challenge(value)

    def test_os_listdir_escape_is_rejected(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        self.assertTrue(candidate.os.listdir("/"))
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_historical_challenge(value)

    def test_urllib_urlopen_escape_is_rejected(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        candidate.urllib.request.urlopen("https://example.invalid")
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_historical_challenge(value)

    def test_dotted_import_is_rejected(self):
        value = challenge("""import candidate
import unittest
import unittest.mock

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_historical_challenge(value)

    def test_from_import_is_rejected(self):
        value = challenge("""import candidate
import unittest
from types import SimpleNamespace

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_historical_challenge(value)

    def test_support_modules_are_loaded_and_digest_bound(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_support(self):
        self.assertEqual(candidate.support_value(), 7)
""")
        result = historical.run_control(
            value,
            b"import merge_governor\ndef support_value():\n    return merge_governor.VALUE\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")
        self.assertEqual(set(result["support_sha256"]), set(SUPPORT))
        self.assertTrue(all(len(value) == 64 for value in result["support_sha256"].values()))

    def test_support_set_is_exact(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
""")
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.run_control(
                value,
                b"VALUE = True\n",
                {"merge_governor.py": b"VALUE = 1\n"},
                candidate_sha="control",
            )
        with self.assertRaises(historical.HistoricalChallengeError):
            historical.validate_support_files({
                **SUPPORT,
                "../escape.py": b"VALUE = 1\n",
            })

    def test_pathlib_external_read_is_blocked_at_runtime(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_read(self):
        with self.assertRaises(RuntimeError):
            candidate.read_external()
""")
        result = historical.run_control(
            value,
            b"import pathlib\ndef read_external():\n    return pathlib.Path('/etc/hosts').read_text()\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_os_open_external_read_is_blocked_at_runtime(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_read(self):
        with self.assertRaises(RuntimeError):
            candidate.read_external()
""")
        result = historical.run_control(
            value,
            b"import os\ndef read_external():\n    return os.open('/etc/hosts', os.O_RDONLY)\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_relative_pathlib_write_inside_workspace_is_allowed(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_write(self):
        candidate.write_local()
        self.assertTrue(True)
""")
        result = historical.run_control(
            value,
            b"import pathlib\ndef write_local():\n    pathlib.Path('result.json').write_text('ok', encoding='utf-8')\n",
            SUPPORT,
            candidate_sha="control",
        )
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_pair_detects_only_fail_candidate_pass_repair(self):
        value = challenge("""import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertEqual(candidate.VALUE, 2)
""")
        result = historical.run_pair(
            value,
            b"VALUE = 1\n",
            b"VALUE = 2\n",
            SUPPORT,
            candidate_sha="bad",
            repair_sha="good",
        )
        self.assertEqual(result["candidate"]["status"], "FAIL")
        self.assertEqual(result["repair"]["status"], "PASS")
        self.assertEqual(result["outcome"], "DETECTED")


if __name__ == "__main__":
    unittest.main()
