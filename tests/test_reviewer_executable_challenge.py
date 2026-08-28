import unittest

from scripts import reviewer_executable_challenge as rec


RATIONALE = "Exercise a bounded executable verification challenge safely."


def make_challenge(code: str, name: str = "challenge_synthetic_case") -> dict[str, str]:
    return {
        "schema": rec.SCHEMA,
        "name": name,
        "rationale": RATIONALE,
        "code": code,
    }


PASS_CODE = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertEqual(candidate.VALUE, 2)
"""


class ReviewerExecutableChallengeTest(unittest.TestCase):
    def test_minimal_valid_challenge_is_accepted(self):
        value = rec.validate_challenge(make_challenge(PASS_CODE))
        self.assertEqual(value["code"], PASS_CODE)
        self.assertEqual(len(rec.challenge_digest(value)), 64)

    def test_extra_keys_fail_closed(self):
        value = make_challenge(PASS_CODE)
        value["unexpected"] = "no"
        with self.assertRaises(rec.UnsafeChallenge):
            rec.validate_challenge(value)

    def test_forbidden_import_fails_closed(self):
        code = """import candidate
import os
import unittest

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
"""
        with self.assertRaises(rec.UnsafeChallenge):
            rec.validate_challenge(make_challenge(code))

    def test_reflective_getattr_escape_is_rejected(self):
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        builtins_map = getattr(candidate, "__builtins__")
        self.assertIsNotNone(builtins_map)
"""
        with self.assertRaises(rec.UnsafeChallenge):
            rec.validate_challenge(make_challenge(code))

    def test_reflective_vars_escape_is_rejected(self):
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_escape(self):
        self.assertIn("__builtins__", vars(candidate))
"""
        with self.assertRaises(rec.UnsafeChallenge):
            rec.validate_challenge(make_challenge(code))

    def test_top_level_execution_fails_closed(self):
        code = """import candidate
import unittest
candidate.VALUE

class CandidateTest(unittest.TestCase):
    def test_value(self):
        self.assertTrue(candidate.VALUE)
"""
        with self.assertRaises(rec.UnsafeChallenge):
            rec.validate_challenge(make_challenge(code))

    def test_pair_requires_fail_candidate_pass_repair(self):
        result = rec.run_pair(
            make_challenge(PASS_CODE),
            b"VALUE = 1\n",
            b"VALUE = 2\n",
            candidate_sha="bad",
            repair_sha="good",
        )
        self.assertEqual(result["candidate"]["status"], "FAIL")
        self.assertEqual(result["repair"]["status"], "PASS")
        self.assertEqual(result["outcome"], "DETECTED")
        self.assertEqual(result["challenge_sha256"], rec.challenge_digest(rec.validate_challenge(make_challenge(PASS_CODE))))

    def test_pair_without_causal_distinction_does_not_detect(self):
        result = rec.run_pair(
            make_challenge(PASS_CODE),
            b"VALUE = 2\n",
            b"VALUE = 2\n",
        )
        self.assertEqual(result["outcome"], "NO_CAUSAL_DISTINCTION")

    def test_control_pass_and_failure_have_distinct_outcomes(self):
        clean = rec.run_control(make_challenge(PASS_CODE), b"VALUE = 2\n")
        dirty = rec.run_control(make_challenge(PASS_CODE), b"VALUE = 1\n")
        self.assertEqual(clean["outcome"], "CLEAN_CONTROL")
        self.assertEqual(dirty["outcome"], "FALSE_POSITIVE")

    def test_network_capability_is_blocked_at_runtime(self):
        source = b"""import socket

def try_network():
    return socket.create_connection((\"127.0.0.1\", 9), timeout=0.05)
"""
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_network_blocked(self):
        with self.assertRaises(RuntimeError):
            candidate.try_network()
"""
        result = rec.run_control(make_challenge(code), source)
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_process_creation_is_blocked_at_runtime(self):
        source = b"""import subprocess

def spawn():
    return subprocess.run([\"/bin/true\"], check=False)
"""
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_process_blocked(self):
        with self.assertRaises(RuntimeError):
            candidate.spawn()
"""
        result = rec.run_control(make_challenge(code), source)
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_arbitrary_file_read_is_blocked_at_runtime(self):
        source = b"""def read_host_file():
    with open(\"/etc/hosts\", \"r\", encoding=\"utf-8\") as handle:
        return handle.read()
"""
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_file_read_blocked(self):
        with self.assertRaises(RuntimeError):
            candidate.read_host_file()
"""
        result = rec.run_control(make_challenge(code), source)
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_directory_enumeration_is_blocked_at_runtime(self):
        source = b"""import os

def enumerate_root():
    return os.listdir(\"/\")
"""
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_directory_read_blocked(self):
        with self.assertRaises(RuntimeError):
            candidate.enumerate_root()
"""
        result = rec.run_control(make_challenge(code), source)
        self.assertEqual(result["outcome"], "CLEAN_CONTROL")

    def test_parent_secrets_are_not_in_child_environment(self):
        old_albert = rec.os.environ.get("ALBERT_API_KEY")
        old_github = rec.os.environ.get("GITHUB_TOKEN")
        rec.os.environ["ALBERT_API_KEY"] = "should-not-cross"
        rec.os.environ["GITHUB_TOKEN"] = "should-not-cross"
        try:
            source = b"""import os

def secrets():
    return os.environ.get(\"ALBERT_API_KEY\"), os.environ.get(\"GITHUB_TOKEN\")
"""
            code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_secrets_absent(self):
        self.assertEqual(candidate.secrets(), (None, None))
"""
            result = rec.run_control(make_challenge(code), source)
            self.assertEqual(result["outcome"], "CLEAN_CONTROL")
        finally:
            if old_albert is None:
                rec.os.environ.pop("ALBERT_API_KEY", None)
            else:
                rec.os.environ["ALBERT_API_KEY"] = old_albert
            if old_github is None:
                rec.os.environ.pop("GITHUB_TOKEN", None)
            else:
                rec.os.environ["GITHUB_TOKEN"] = old_github

    def test_timeout_is_unproven(self):
        source = b"""def spin():
    while True:
        pass
"""
        code = """import candidate
import unittest

class CandidateTest(unittest.TestCase):
    def test_spin(self):
        candidate.spin()
"""
        challenge = make_challenge(code)
        result = rec.run_pair(
            challenge,
            source,
            b"def spin():\n    return None\n",
            timeout_seconds=0.2,
        )
        self.assertEqual(result["candidate"]["status"], "TIMEOUT")
        self.assertEqual(result["outcome"], "UNPROVEN")


if __name__ == "__main__":
    unittest.main()
