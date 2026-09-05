"""P346 uses the same real C supervisor/socket qualification as P345."""
import unittest
import test_s22plus_fyg8_p345_c_host_join as predecessor_tests
import s22plus_fyg8_p346_research_shell_runtime as runtime


class CJoinTests(predecessor_tests.CJoinTests):
    runtime = runtime


if __name__ == "__main__":
    unittest.main()
