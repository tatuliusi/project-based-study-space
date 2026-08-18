import os
import unittest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from src.graph import ask
from src.retriever import build_vectorstore


class Project01QualityChecks(unittest.TestCase):
    def test_blank_query_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            ask("   ", None)

    def test_build_vectorstore_requires_files(self):
        with self.assertRaisesRegex(ValueError, "at least one file"):
            build_vectorstore([])


if __name__ == "__main__":
    unittest.main()
