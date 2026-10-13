# Test coverage matrix (SPEC rule ID -> tests)

Updated for D-12 (C-1.11, C-1.12) and the SPEC v1.2 check order on 2026-10-13, after the T-005 security review.

| File | Covers |
|---|---|
| `test_create.py` | C |
| `test_report.py` | O, R-1 (bounds), R-3, T-1, T-2 |
| `test_settle.py` | S, T-3 |
| `test_objection.py` | X, T-4 (objection side) |
| `test_finalize_withdraw.py` | F, P, T-4 (finalize side) |
| `test_scenarios.py` | SPEC §6 end-to-end runs |
| `test_views.py` | V, R-1 (deploy checks) |
| `helpers/RejectingRenter.vy`, `helpers/ReentrantRenter.vy` | test-only payee contracts (P-3; P-2: the hook records `credits(self)`, re-enters `settle`/`finalize`/`raise_objection`/`create_rental` as armed, then `withdraw`) |

State on 2026-10-13, after the check-order hardening: `pytest -q tests/` -> 253 passed, 0 failed
(253 tests). `contracts/GpuSlaEscrow.vy` implements C-1.11 and C-1.12. No test body is TODO.

SPEC v1.2 check order (C-1.1..C-1.9, then C-1.11, then C-1.12; the earlier rule's string wins)
is pinned by the `test_C_order_*` tests, the only tests that violate two rules at once:

| Double violation | Expected string | Test |
|---|---|---|
| C-1.9 + C-1.11 (257 slots, start = now + 30 days + 1) | `too many slots` | `test_C_order_too_many_slots_wins_over_start_too_far` |
| C-1.9 + C-1.12 (257 slots of 86401 s) | `too many slots` | `test_C_order_too_many_slots_wins_over_interval_too_long` |
| C-1.11 + C-1.12 (start = now + 30 days + 1, interval 86401, 1 and 256 slots) | `start too far` | `test_C_order_start_too_far_wins_over_interval_too_long[1,256]` |
| C-1.2 + C-1.3 (end == start, interval 0) | `end before start` | `test_C_order_end_before_start_wins_over_zero_interval` |
| C-1.1 + C-1.5 (start = now - 1, threshold 0) | `start in past` | `test_C_order_start_in_past_wins_over_bad_threshold` |

The other adjacent pairs of C-1.1..C-1.8 are not pinned pairwise.

D-12 tests validated by mutation (copies of the real contract kept outside the repo, pytest run
with the copy's directory as cwd; each run 253 tests):

| Mutant of `create_rental` | Red tests |
|---|---|
| (a) C-1.11 and C-1.12 asserts moved above C-1.9 | `test_C_order_too_many_slots_wins_over_start_too_far`, `test_C_order_too_many_slots_wins_over_interval_too_long` |
| (b) C-1.11 and C-1.12 swapped | `test_C_order_start_too_far_wins_over_interval_too_long[1]`, `[256]` |
| (c) `start < now + MAX_START_DELAY` | `test_C_1_11_start_exactly_30_days_ahead_accepted`, `test_C_1_12_max_size_rental_settles_and_refunds_without_overflow` |
| (d) `interval < MAX_INTERVAL` | `test_C_1_12_interval_one_day_accepted[1]`, `[256]`, `test_C_1_12_max_size_rental_settles_and_refunds_without_overflow` |

Re-entrancy tests validated by mutation (copies of the real contract kept outside the repo,
tests pointed at them by running pytest from the copy's directory):

| Mutant of `withdraw()` | Red tests |
|---|---|
| (a) credit zeroed **after** the `raw_call`, `@nonreentrant` kept | `test_P_2_credit_reads_zero_during_the_transfer`, `test_P_2_nested_withdraw_of_a_fresh_credit_is_locked_out`, `test_P_2_cross_function_reentry_keeps_the_escrow_solvent` |
| (b) `@nonreentrant` removed, credit zeroed first | `test_P_2_nested_withdraw_of_a_fresh_credit_is_locked_out`, `test_P_2_cross_function_reentry_keeps_the_escrow_solvent` |

`test_P_2_reentrant_payee_gains_nothing` (the only re-entrancy test before T-005) stays green
under both mutants: with one defence left the attacker still gains nothing. It checks the
outcome "no theft", not either defence; the three tests above are the ones that pin P-2.
The 21-mutant run recorded at T-003 was against a throwaway implementation, not this contract,
and has not been repeated here.

Every SPEC rule ID that the contract can enforce has a test. The only IDs without a test in
`tests/` are the off-chain ones (R-2, H-1..H-7), listed at the end.

## C — create_rental (`test_create.py`)

| ID | Revert string | Tests |
|---|---|---|
| C-1.1 | `start in past` | `test_C_1_1_start_in_past_reverts`, `test_C_1_1_start_equal_to_now_accepted` |
| C-1.2 | `end before start` | `test_C_1_2_end_equal_to_start_reverts`, `test_C_1_2_end_before_start_reverts` |
| C-1.3 | `zero interval` | `test_C_1_3_zero_interval_reverts` |
| C-1.4 | `not multiple` | `test_C_1_4_duration_not_multiple_reverts`, `test_C_1_4_duration_off_by_one_second_reverts[-1,1]`, `test_C_1_4_duration_shorter_than_interval_reverts` |
| C-1.5 | `bad threshold` | `test_C_1_5_threshold_out_of_range_reverts[0,101]`, `test_C_1_5_threshold_boundary_accepted[1,100]` |
| C-1.6 | `zero provider` | `test_C_1_6_zero_provider_reverts` |
| C-1.7 | `renter is provider` | `test_C_1_7_renter_is_provider_reverts` |
| C-1.8 | `no value` | `test_C_1_8_no_value_reverts`, `test_C_1_8_price_is_msg_value` |
| C-1.9 | `too many slots` | `test_C_1_9_max_slots_256_accepted`, `test_C_1_9_257_slots_reverts`, `test_C_1_9_n_slots_is_duration_over_interval` |
| C-1.11 | `start too far` | `test_C_1_11_start_exactly_30_days_ahead_accepted`, `test_C_1_11_start_30_days_plus_one_second_reverts`, `test_C_1_11_huge_start_reverts_with_string_not_panic` (`start = 2**255`) |
| C-1.12 | `interval too long` | `test_C_1_12_interval_one_day_accepted[1,256]`, `test_C_1_12_interval_one_day_plus_one_second_reverts[1,256]`, `test_C_1_12_end_max_uint_one_slot_reverts_with_string_not_panic` (`end = 2**256 - 1`), `test_C_1_12_max_size_rental_settles_and_refunds_without_overflow` (start +30 days, 256 one-day slots: views answer; slot 255 reported Up at exactly `end`, `end - 1` reverts `slot not done`; 1/256 Up at threshold 75 is non-compliant, so settle / finalize / withdraw refund the renter) |
| C check order | earlier rule's string | the five `test_C_order_*` tests (table above) |
| C-1.10 | — | `test_C_1_10_happy_path`, `test_C_1_10_ids_increment_from_one`, `test_C_1_10_all_fields_stored`, `test_C_1_10_balance_grows_by_exactly_msg_value`, `test_C_1_10_rental_created_event`, `test_C_1_10_different_renters_get_their_own_rental` |

## O — report_uptime (`test_report.py`)

| ID | Revert string | Tests |
|---|---|---|
| O-1 | `not reporter` | `test_O_1_stranger_reverts`, `test_O_1_renter_and_provider_are_not_reporters`, `test_O_1_either_allow_listed_reporter_accepted[0,1]`, `test_O_1_two_reporters_can_share_one_rental` |
| O-2 | `not active` | `test_O_2_nonexistent_rental_reverts[0,1,99]`, `test_O_2_next_unused_id_reverts`; Proposed and Settled status: `test_scenarios.py::test_scenario_report_after_settle_reverts_not_active` |
| O-3 (T-2) | `reporting closed` | `test_O_3_report_at_end_plus_grace_accepted`, `test_O_3_report_one_second_after_grace_reverts`, `test_O_3_window_closes_between_two_reports`, `test_O_3_long_after_end_reverts` |
| O-4 | `bad slot` | `test_O_4_slot_equal_to_n_slots_reverts`, `test_O_4_last_slot_accepted` |
| O-5 (T-1) | `slot not done` | `test_O_5_one_second_before_slot_completion_reverts[0..3]`, `test_O_5_exactly_at_slot_completion_accepted[0..3]`, `test_O_5_running_slot_reverts`, `test_O_5_future_slot_reverts`, `test_O_5_before_start_reverts` |
| O-6 | `already reported` | `test_O_6_duplicate_reverts_and_changes_nothing[up/down x up/down]`, `test_O_6_duplicate_from_other_reporter_reverts`, `test_O_6_duplicate_later_in_grace_reverts` |
| O success effects | — | `test_O_success_up_stores_1_and_counts`, `test_O_success_down_stores_2_and_does_not_count_up`, `test_O_success_changes_only_counts`, `test_O_success_emits_uptime_reported[True,False]`, `test_O_full_run_slot_by_slot` |
| O backfill | — | `test_O_backfill_earlier_empty_slot_accepted`, `test_O_backfill_all_slots_in_reverse_at_grace_deadline` |

## S — settle (`test_settle.py`)

| ID | Revert string | Tests |
|---|---|---|
| S-1 | `not active` | `test_S_1_nonexistent_rental_reverts[0,1,99]`, `test_S_1_double_settle_reverts`, `test_S_1_settle_after_finalize_reverts` |
| S-2 (T-3) | `too early` | `test_S_2_settle_at_end_plus_grace_reverts`, `test_S_2_settle_one_second_after_grace_succeeds`, `test_S_2_settle_before_grace_is_over_reverts[created,start,mid,end-1,end,end+grace-1]`, `test_T_3_report_and_settle_windows_never_overlap` |
| S-3 | — | `test_S_3_compliance_is_100_up_ge_threshold_n[16 threshold/N/M cases]`, `test_S_3_boundary_equal_is_compliant`, `test_S_3_unreported_slots_count_as_down`, `test_S_3_denominator_is_n_slots_not_reported_count`, `test_S_3_no_reports_at_all_refunds_renter` |
| S-4 | — | `test_S_4_stores_status_proposed_at_and_compliant[compliant,non-compliant]` (exactly three fields change, no MON moves, no credit), `test_S_4_settle_touches_only_its_own_rental` |
| S-5 | — | `test_S_5_settlement_proposed_event[compliant,non-compliant]` (all 8 fields), `test_S_5_amount_is_the_rental_price`, `test_S_5_same_result_for_any_caller[renter,provider,stranger,reporter x 2]`, `test_S_5_same_result_when_settled_much_later[x2]` |

## X — raise_objection (`test_objection.py`)

| ID | Revert string | Tests |
|---|---|---|
| X-1 | `not proposed` | `test_X_1_active_rental_reverts[running,grace,settleable x renter,provider]`, `test_X_1_settled_rental_reverts[renter,provider]`, `test_X_1_nonexistent_rental_reverts[0,1,99]` |
| X-2 (T-4) | `window closed` | `test_X_2_objection_in_last_second_of_window_succeeds[x2]`, `test_X_2_objection_at_window_end_reverts[x2]`, `test_X_2_objection_in_same_second_as_settle_succeeds`, `test_X_2_objection_long_after_window_reverts`, `test_X_2_window_counts_from_proposed_at_not_from_end` |
| X-3 | `not a party` | `test_X_3_non_party_reverts[stranger,reporter]`, `test_X_3_settle_caller_is_not_a_party`, `test_X_3_party_of_another_rental_reverts` |
| X-4 | `already objected` | `test_X_4_second_objection_by_same_party_reverts[x2]`, `test_X_4_both_parties_can_each_object_once`, `test_X_4_provider_first_then_renter`, `test_X_4_objection_raised_event[x2]` (rental_id, by, is_renter), `test_X_4_changes_nothing_but_the_callers_flag[x4]`, `test_X_4_objection_does_not_change_payee_or_amount[none/renter/provider/both x 2]` |

## F — finalize (`test_finalize_withdraw.py`)

| ID | Revert string | Tests |
|---|---|---|
| F-1 | `not proposed` | `test_F_1_active_rental_reverts[running,settleable,long after]`, `test_F_1_nonexistent_rental_reverts[0,1,99]`, `test_F_1_double_finalize_reverts[x2]` |
| F-2 (T-4) | `window open` | `test_F_2_finalize_one_second_before_window_end_reverts`, `test_F_2_finalize_at_window_end_succeeds`, `test_F_2_finalize_in_same_second_as_settle_reverts`, `test_F_2_finalize_long_after_window_succeeds`, `test_F_2_window_counts_from_proposed_at_not_from_end`, `test_T_4_objection_and_finalize_windows_never_overlap` |
| F-3 | — | `test_F_3_status_becomes_settled_and_nothing_else_changes[x2]`, `test_F_3_settled_rental_cannot_be_credited_again`. The order "Settled **before** crediting" cannot be observed from outside because `finalize` makes no external call: code inspection in T-005. |
| F-4 | — | `test_F_4_credits_payee_with_price[x2]`, `test_F_4_finalize_transfers_nothing[x2]` (no external call: every balance unchanged), `test_F_4_settlement_finalized_event[x2]` (all 4 fields), `test_F_4_anyone_can_finalize[x4]`, `test_F_4_credits_accumulate_over_two_rentals` (`+=`), `test_F_4_one_address_credited_as_provider_and_as_renter`, `test_P_3_rejecting_payee_fails_only_its_own_withdraw` (a rejecting payee cannot block `finalize`) |

## P — withdraw (`test_finalize_withdraw.py`)

| ID | Revert string | Tests |
|---|---|---|
| P-1 | `nothing to withdraw` | `test_P_1_no_credit_reverts`, `test_P_1_losing_party_and_bystanders_have_nothing_to_withdraw[x2]`, `test_P_1_payee_cannot_withdraw_before_finalize`, `test_P_1_withdraw_sends_exactly_the_credit[x2]`, `test_P_1_withdraw_takes_only_the_callers_credit` |
| P-2 | — | `test_P_2_credit_zeroed_and_second_withdraw_reverts`, `test_P_2_reentrant_payee_gains_nothing` (outcome only: no theft), `test_P_2_credit_reads_zero_during_the_transfer` (zero-first: `credits(self)` read inside the receive hook is 0), `test_P_2_nested_withdraw_of_a_fresh_credit_is_locked_out` (`@nonreentrant`: the hook finalizes a second rental to itself, the nested `withdraw` fails, the credit survives and is paid by a later call), `test_P_2_cross_function_reentry_keeps_the_escrow_solvent` (hook calls `settle`, `finalize`, `raise_objection`, `create_rental`; `balance == prices of Active/Proposed + credits`) — all with `helpers/ReentrantRenter.vy` |
| P-3 | `transfer failed` | `test_P_3_withdrawn_event[x2]` (account, amount), `test_P_3_rejecting_payee_fails_only_its_own_withdraw` (`helpers/RejectingRenter.vy`) |

## R — Reporters

| ID | Tests |
|---|---|
| R-1 | `test_views.py`: `test_R_1_reporters_allow_listed`, `test_R_1_empty_reporter_list_reverts`, `test_R_1_zero_address_reporter_reverts[first,middle,last]`, `test_R_1_only_zero_address_reverts`; `test_report.py`: `test_R_1_eight_reporters_accepted`, `test_R_1_nine_reporters_rejected`, `test_R_1_reporter_set_unchanged_by_create_and_report` |
| R-3 | `test_R_3_report_touches_only_its_own_rental`, `test_R_3_same_slot_index_is_independent_per_rental`, `test_R_two_rentals_reported_by_two_keys`; that no global slot is written is also code inspection (T-005) |

## T — Timing

| ID | Edge | Tests |
|---|---|---|
| T-1 | `start + (k+1)*interval` | the O-5 tests (both sides, every k); at the largest allowed values (k = 255, one-day slots, start +30 days) in `test_C_1_12_max_size_rental_settles_and_refunds_without_overflow` |
| T-2 | `end + REPORT_GRACE` ok, `+1` reverts | the O-3 tests |
| T-3 | `end + REPORT_GRACE` reverts, `+1` ok | the S-2 tests, `test_T_3_report_and_settle_windows_never_overlap` |
| T-4 | `proposed_at + CHALLENGE_WINDOW - 1`: objection ok, finalize reverts; at the boundary: objection reverts, finalize ok | the X-2 and F-2 tests, `test_T_4_objection_and_finalize_windows_never_overlap` |

## V — Views (`test_views.py`)

| View | Tests |
|---|---|
| `phase` 0 | `test_V_unknown_rental_is_phase_none` |
| `phase` 1..4 (both sides of `start`, `end`, `end + REPORT_GRACE`) | `test_V_phase_both_sides_of_start_end_and_grace`, `test_V_phase_does_not_depend_on_reports` |
| `phase` 5..7 (both sides of `proposed_at + CHALLENGE_WINDOW`, after finalize) | `test_V_phase_both_sides_of_challenge_window_and_settled`, `test_V_phase_settled_after_withdraw`; also walked 1 -> 7 in `test_scenario_compliant_run_provider_withdraws_price` |
| `payout_preview` before settle | `test_V_payout_preview_tracks_reports_before_settle`, `test_V_payout_preview_unknown_rental` |
| `payout_preview` after settle | `test_V_payout_preview_frozen_after_settle[4,3,2,0 Up]` |
| `credits` | `test_V_credits_zero_until_finalize`, all F-4 / P tests |
| `next_rental_id` | `test_V_ids_start_at_one`, C-1.10 tests |
| `REPORT_GRACE`, `CHALLENGE_WINDOW` | `test_V_constants` |
| `is_reporter` | `test_R_1_reporters_allow_listed` |
| `rentals`, `get_slots` | `test_V_unknown_rental_is_phase_none`; asserted throughout C-1.10, O, S-4, X-4, F-3 tests |

## SPEC §6 scenarios

| Scenario | Test |
|---|---|
| Full compliant run (4/4, provider withdraws exactly `price`) | `test_scenario_compliant_run_provider_withdraws_price` |
| Full non-compliant run (2/4 at 75, renter refunded) | `test_scenario_non_compliant_run_renter_refunded` |
| Boundary `100*M == threshold*N` (3/4 at 75) | `test_scenario_boundary_three_of_four_at_75_passes`, `test_S_3_boundary_equal_is_compliant` |
| Unreported slots count as down | `test_scenario_unreported_slots_count_as_down`, `test_S_3_unreported_slots_count_as_down` |
| Objection by each party has no effect | `test_scenario_objection_by_each_party_has_no_effect[x2]`, `test_X_4_objection_does_not_change_payee_or_amount[x8]` |
| Settle and finalize by a third wallet | `test_scenario_third_wallet_settles_and_finalizes` |
| Same result when settled much later | `test_scenario_same_result_when_settled_much_later`, `test_S_5_same_result_when_settled_much_later[x2]` |
| Double settle / finalize / withdraw revert | `test_scenario_double_settle_finalize_withdraw_revert` |
| One address credited by two rentals gets the sum | `test_F_4_credits_accumulate_over_two_rentals` |
| Re-entering payee gains nothing | `test_P_2_reentrant_payee_gains_nothing`, `test_P_2_credit_reads_zero_during_the_transfer`, `test_P_2_nested_withdraw_of_a_fresh_credit_is_locked_out`, `test_P_2_cross_function_reentry_keeps_the_escrow_solvent` |
| Far-future `end` (`2**256 - 1`) is refused with a table E string, a normal rental afterwards runs its full compliant lifecycle | `test_scenario_far_future_end_rejected_and_normal_rental_runs_full_lifecycle` |
| Rejecting payee fails only its own withdraw | `test_P_3_rejecting_payee_fails_only_its_own_withdraw` |
| Report after settle reverts `not active` | `test_scenario_report_after_settle_reverts_not_active` |
| Reports for 2 rentals from 2 keys | `test_R_two_rentals_reported_by_two_keys`, `test_scenario_two_rentals_two_keys_settle_independently` |

## Off-chain rules — no test possible in `tests/`

| ID | Where it is tested |
|---|---|
| R-2 (oracle picks `keys[rental_id % len(keys)]`) | oracle tests, T-009. Contract side: the two "2 rentals, 2 keys" tests above |
| H-1 .. H-7 (oracle service) | `oracle/tests/`, T-008..T-010, T-013 |

## Not covered on purpose — owner decision pending

| Behaviour | Status |
|---|---|
| `settle`, `finalize`, `raise_objection`, `create_rental` are callable from inside a `withdraw` transfer | SPEC P-2 locks `withdraw` only. The cross-function test relies on this as a precondition (asserted with a message) and checks solvency, not that it must stay so. |
