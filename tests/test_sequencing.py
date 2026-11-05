import pytest
from handlers.sequencing import SequencingHandler

def test_sequencing_modal_rules():
    handler = SequencingHandler()

    words1 = ["do", "couldn't", "yoga.", "He"]
    candidates1 = handler._get_candidate_orders(words1)
    assert len(candidates1) > 0
    top1 = candidates1[0]
    assert top1 == ["He", "couldn't", "do", "yoga."]

    words2 = ["relax.", "help", "Yoga", "you", "may"]
    candidates2 = handler._get_candidate_orders(words2)
    assert len(candidates2) > 0
    top2 = candidates2[0]
    assert top2 == ["Yoga", "may", "help", "you", "relax."]

def test_sequencing_prefix_aware_suffix():
    handler = SequencingHandler()
    prefix = ["I", "may"]
    remaining_words = ["be", "not", "to.", "able"]

    candidates = handler._get_candidate_orders(remaining_words, prefix=prefix)
    assert len(candidates) > 0
    top = candidates[0]
    assert top == ["not", "be", "able", "to."]

def test_sequencing_failure_memory():
    handler = SequencingHandler()
    words = ["do", "couldn't", "yoga.", "He"]

    top1 = handler._get_candidate_orders(words)[0]
    handler._failed_permutations.add(tuple(top1))

    candidates_after = handler._get_candidate_orders(words)
    assert tuple(top1) not in [tuple(c) for c in candidates_after]
