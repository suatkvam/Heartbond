"""Views already implemented in the skeleton — these pass from day 0."""
import boa


def test_V_unknown_rental_is_phase_none(escrow):
    assert escrow.phase(1) == 0
    assert escrow.get_slots(1) == []


def test_V_ids_start_at_one(escrow):
    assert escrow.next_rental_id() == 1


def test_V_constants(escrow):
    assert escrow.REPORT_GRACE() == 30
    assert escrow.CHALLENGE_WINDOW() == 60


def test_R_1_reporters_allow_listed(escrow, reporters, stranger):
    assert all(escrow.is_reporter(r) for r in reporters)
    assert not escrow.is_reporter(stranger)


def test_R_1_empty_reporter_list_reverts():
    with boa.reverts("no reporters"):
        boa.load("contracts/GpuSlaEscrow.vy", [])
