"""Headless tests for the coach store (design.md, section 9, step 1).

Run:  conda run -n sleep_enforcer_windows_env python -m pytest test_coach.py -q
  or: conda run -n sleep_enforcer_windows_env python test_coach.py

No GUI is created. The database lives in a temp file that is deleted at the end.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coach.schemas import (
    ActivitySample,
    Classification,
    EventRecord,
    TaskDetails,
)
from coach.store import Store
from coach.classifier import Classifier
from coach.recommender import Recommender
from coach.explainer import build_explanation, build_comparison


def make_store() -> Store:
    """A Store backed by a fresh temp database."""
    tmp = tempfile.mktemp(suffix=".db")
    store = Store(db_path=tmp)
    store.open()
    return store


def make_event(**overrides) -> EventRecord:
    now = datetime.now()
    base = dict(
        started_at=now,
        schedule_bedtime=now,
        choice="continue",
        extension_used=False,
        task=TaskDetails(
            description="fixing bug",
            category="work",
            urgency=4,
            importance=4,
            est_minutes=30,
            goal_tags=["Finish my degree with good grades"],
            source="user",
        ),
        activity=ActivitySample(
            program_name="code.exe",
            mapped_category="work",
            user_corrected=False,
        ),
    )
    base.update(overrides)
    return EventRecord(**base)


# ---------------------------------------------------------------
# Test 1: save + load round-trip
# ---------------------------------------------------------------
def test_save_and_reload_event():
    store = make_store()
    try:
        event = make_event()
        event_id = store.save_event(event)

        loaded = store.get_event(event_id)
        assert loaded is not None, "event not found after save"
        assert loaded.choice == "continue"
        assert loaded.task.category == "work"
        assert loaded.task.urgency == 4
        assert loaded.task.goal_tags == ["Finish my degree with good grades"]
        assert loaded.activity.program_name == "code.exe"
        assert loaded.activity.mapped_category == "work"
        assert loaded.resolved_at is None  # not resolved yet
        print("[SUCCESS] Test 1: save/load round-trip passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 2: resolve_event updates choice and flags
# ---------------------------------------------------------------
def test_resolve_event():
    store = make_store()
    try:
        event_id = store.save_event(make_event(choice=""))
        store.resolve_event(
            event_id,
            choice="sleep",
            extension_used=False,
            recommended_choice="sleep",
            recommendation_followed=True,
        )
        loaded = store.get_event(event_id)
        assert loaded.choice == "sleep"
        assert loaded.resolved_at is not None
        assert loaded.recommendation_followed is True
        print("[SUCCESS] Test 2: resolve_event passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 3: extension_used_tonight (one-extension-per-night cap)
# ---------------------------------------------------------------
def test_extension_used_tonight():
    store = make_store()
    try:
        now = datetime.now()
        assert store.extension_used_tonight(now) is False, \
            "no events yet, extension must be available"

        # An extension 2 hours ago -> tonight's extension is spent.
        store.save_event(make_event(
            started_at=now - timedelta(hours=2),
            extension_used=True,
            resolved_at=now - timedelta(hours=2),
        ))
        assert store.extension_used_tonight(now) is True

        # An extension 3 days ago -> a new night, extension available again.
        store2 = make_store()
        try:
            store2.save_event(make_event(
                started_at=now - timedelta(days=3),
                extension_used=True,
                resolved_at=now - timedelta(days=3),
            ))
            assert store2.extension_used_tonight(now) is False, \
                "old extension must not block tonight"
        finally:
            store2.close()
            os.remove(store2.db_path)
        print("[SUCCESS] Test 3: extension cap lookup passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 4: outcomes and events_needing_feedback
# ---------------------------------------------------------------
def test_outcomes_and_feedback_queue():
    store = make_store()
    try:
        # Two resolved events, one with an outcome already recorded.
        e1 = store.save_event(make_event(choice="continue"))
        store.resolve_event(e1, choice="continue", resolved_at=datetime.now())
        e2 = store.save_event(make_event(choice="replan"))
        store.resolve_event(e2, choice="replan", resolved_at=datetime.now())

        pending = store.events_needing_feedback()
        assert e1 in [e.id for e in pending], "e1 should need feedback"
        assert e2 in [e.id for e in pending], "e2 should need feedback"

        store.save_outcome(e1, reported="finished")
        assert store.outcome_for_event(e1) == "finished"

        pending = store.events_needing_feedback()
        assert e1 not in [e.id for e in pending], \
            "e1 has an outcome now, must leave the queue"
        assert e2 in [e.id for e in pending]

        # no_answer events never ask for feedback
        e3 = store.save_event(make_event(choice="no_answer"))
        store.resolve_event(e3, choice="no_answer", resolved_at=datetime.now())
        assert e3 not in [e.id for e in store.events_needing_feedback()]
        print("[SUCCESS] Test 4: outcomes/feedback queue passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 5: replans
# ---------------------------------------------------------------
def test_replans():
    store = make_store()
    try:
        event_id = store.save_event(make_event(choice="replan"))
        rid = store.save_replan(
            event_id, "Assignment draft",
            target_time=datetime.now() + timedelta(hours=18),
            est_minutes=45,
        )
        open_items = store.open_replans()
        assert len(open_items) == 1
        assert open_items[0]["title"] == "Assignment draft"
        assert open_items[0]["done"] == 0

        store.mark_replan_done(rid)
        assert store.open_replans() == []
        print("[SUCCESS] Test 5: replans passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 6: goals (builtin seeding, add, deactivate, delete)
# ---------------------------------------------------------------
def test_goals():
    store = make_store()
    try:
        # Built-in goals are seeded on first open.
        active = store.active_goals()
        assert len(active) == 4, f"expected 4 builtin goals, got {len(active)}"

        store.add_goal("Ship the side project")
        active = store.active_goals()
        assert len(active) == 5
        assert "Ship the side project" in active

        all_goals = store.all_goals()
        custom = [g for g in all_goals if g["builtin"] == 0][0]
        store.set_goal_active(custom["id"], False)
        assert "Ship the side project" not in store.active_goals()

        # Deleting a built-in only deactivates it, never removes it.
        builtin = [g for g in all_goals if g["builtin"] == 1][0]
        store.delete_goal(builtin["id"])
        assert builtin["text"] not in store.active_goals()
        assert builtin["text"] in [g["text"] for g in store.all_goals()]
        print("[SUCCESS] Test 6: goals passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 7: category rules and classification corrections
# ---------------------------------------------------------------
def test_category_rules_and_corrections():
    store = make_store()
    try:
        store.upsert_category_rule("Steam.exe", "distraction")
        rules = store.user_category_rules()
        assert len(rules) == 1
        assert rules[0]["program_name"] == "steam.exe", \
            "program names must be stored lowercase"

        # Upsert updates instead of duplicating.
        store.upsert_category_rule("steam.exe", "leisure")
        rules = store.user_category_rules()
        assert len(rules) == 1
        assert rules[0]["category"] == "leisure"

        store.remove_category_rule("steam.exe")
        assert store.user_category_rules() == []

        # Corrections are recorded as new rows, never rewriting history.
        event_id = store.save_event(make_event())
        store.save_classification_correction(
            event_id, "chrome.exe", "leisure", "study")
        store.save_classification_correction(
            event_id, "chrome.exe", "leisure", "study")
        store.save_classification_correction(
            event_id, "chrome.exe", "leisure", "work")
        counts = store.correction_counts_for_program("CHROME.exe")
        assert counts == {"study": 2, "work": 1}, f"got {counts}"
        print("[SUCCESS] Test 7: rules/corrections passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 8: export / import / delete_history (FR-11 data controls)
# ---------------------------------------------------------------
def test_export_import_delete():
    store = make_store()
    try:
        e1 = store.save_event(make_event())
        store.resolve_event(e1, choice="continue", resolved_at=datetime.now())
        store.save_outcome(e1, "finished")
        store.add_goal("Custom goal")

        # Export, then delete history, then import back.
        data = store.export_all()
        assert len(data["events"]) == 1
        assert len(data["goals"]) == 5  # 4 builtin + 1 custom

        store.delete_history()
        assert store.export_all()["events"] == []
        assert store.export_all()["outcomes"] == []
        # Goals and user rules survive a history wipe.
        assert len(store.active_goals()) == 5

        store.import_all(data)
        restored = store.export_all()
        assert len(restored["events"]) == 1
        assert len(restored["outcomes"]) == 1
        assert store.outcome_for_event(e1) == "finished"
        print("[SUCCESS] Test 8: export/import/delete passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ---------------------------------------------------------------
# Test 9: corrupt database falls back safely (plan.md NFR resilience)
# ---------------------------------------------------------------
def test_corrupt_db_falls_back():
    tmp = tempfile.mktemp(suffix=".db")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("this is not a database at all")
    try:
        store = Store(db_path=tmp)
        try:
            store.open()
        except Exception:
            pass  # Opening a corrupt file should raise — caller recreates
        try:
            store.close()  # release the handle so Windows lets us delete
        except Exception:
            pass
        # Recreate fresh: delete the bad file and open again.
        if os.path.exists(tmp):
            os.remove(tmp)
        store2 = Store(db_path=tmp)
        store2.open()
        assert store2.active_goals()  # seeded fine
        store2.close()
        print("[SUCCESS] Test 9: corrupt-db fallback passed!")
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass  # still locked; temp dir cleans it up eventually




# ===============================================================
# Classifier tests (design.md section 4)
# ===============================================================

def test_classifier_user_rule_wins():
    store = make_store()
    try:
        classifier = Classifier(store)
        store.upsert_category_rule("chrome.exe", "study")

        result = classifier.classify("chrome.exe")
        assert result.category == "study", f"got {result.category}"
        assert result.source == "user_rule"
        assert result.confidence == 0.95
        assert "Your own rule" in result.evidence
        print("[SUCCESS] Classifier test 1: user rule wins passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_classifier_builtin_known_app():
    store = make_store()
    try:
        classifier = Classifier(store)
        result = classifier.classify("steam.exe")
        assert result.category == "distraction"
        assert result.source == "builtin"
        assert result.confidence >= 0.75
        print("[SUCCESS] Classifier test 2: builtin known app passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_classifier_ambiguous_never_guessed():
    store = make_store()
    try:
        classifier = Classifier(store)
        # A browser must stay unknown from name alone — never guessed as fact.
        result = classifier.classify("chrome.exe")
        assert result.category == "unknown", \
            f"browsers must stay unknown, got {result.category}"
        assert result.source == "unknown"
        assert result.confidence == 0.0
        assert "can be work or play" in result.evidence
        print("[SUCCESS] Classifier test 3: ambiguous stays unknown passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_classifier_learns_from_history():
    store = make_store()
    try:
        classifier = Classifier(store)
        # Correct chrome.exe -> study three times (the minimum evidence bar).
        for _ in range(3):
            classifier.learn_correction(
                None, "chrome.exe", "unknown", "study")

        result = classifier.classify("chrome.exe")
        assert result.category == "study", f"got {result.category}"
        assert result.source == "history"
        assert result.confidence >= 0.5
        assert "From your history" in result.evidence

        # A user rule still outranks history.
        store.upsert_category_rule("chrome.exe", "work")
        assert classifier.classify("chrome.exe").source == "user_rule"
        print("[SUCCESS] Classifier test 4: learns from history passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_classifier_correction_never_rewrites_history():
    store = make_store()
    try:
        classifier = Classifier(store)
        event_id = store.save_event(make_event(
            activity=ActivitySample(
                program_name="chrome.exe",
                mapped_category="unknown",
                user_corrected=False,
            )
        ))
        classifier.learn_correction(event_id, "chrome.exe", "unknown", "study")

        # Past event untouched; a NEW feedback row was added.
        loaded = store.get_event(event_id)
        assert loaded.activity.mapped_category == "unknown"
        assert loaded.activity.user_corrected is False
        counts = store.correction_counts_for_program("chrome.exe")
        assert counts == {"study": 1}
        print("[SUCCESS] Classifier test 5: correction adds, never rewrites passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ===============================================================
# Recommender tests (design.md section 5)
# ===============================================================

def make_task(**overrides) -> TaskDetails:
    base = dict(category="study", urgency=3, importance=3,
                est_minutes=30, source="user")
    base.update(overrides)
    return TaskDetails(**base)


def seed_continue_with_outcome(store, outcome, **task_overrides):
    """A past night where the user continued and reported `outcome`."""
    when = datetime.now() - timedelta(days=1)
    eid = store.save_event(make_event(
        started_at=when, resolved_at=when, choice="continue",
        task=make_task(**task_overrides),
    ))
    store.save_outcome(eid, reported=outcome, asked_at=when)


def test_recommender_urgent_task_continue_wins():
    store = make_store()
    try:
        rec = Recommender(store).recommend(
            make_task(urgency=5, importance=5, est_minutes=20),
            extension_available=True,
        )
        assert rec.recommended_choice == "continue", \
            f"urgent+important should recommend continue, got {rec.recommended_choice}"
        assert rec.limited_data is True  # no history yet
        print("[SUCCESS] Recommender test 1: urgent -> continue passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_recommender_extension_used_blocks_continue():
    store = make_store()
    try:
        rec = Recommender(store).recommend(
            make_task(urgency=5, importance=5),
            extension_available=False,
        )
        continue_opt = [o for o in rec.options if o.choice == "continue"][0]
        assert continue_opt.score == 0
        assert rec.recommended_choice != "continue"
        assert rec.continue_available is False
        print("[SUCCESS] Recommender test 2: extension cap blocks continue passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_recommender_important_not_urgent_late_replans():
    store = make_store()
    try:
        # Seed history: several bad late-night continues.
        for _ in range(3):
            seed_continue_with_outcome(store, "regretted")

        rec = Recommender(store).recommend(
            make_task(urgency=1, importance=5, est_minutes=60),
            extension_available=True,
        )
        assert rec.recommended_choice == "replan", \
            f"important+not urgent+bad history should replan, got {rec.recommended_choice}"
        assert rec.limited_data is False
        print("[SUCCESS] Recommender test 3: important-not-urgent -> replan passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_recommender_sleep_wins_on_distraction():
    store = make_store()
    try:
        rec = Recommender(store).recommend(
            make_task(category="distraction", urgency=1, importance=1),
            extension_available=True,
        )
        assert rec.recommended_choice == "sleep", \
            f"low-stakes distraction should sleep, got {rec.recommended_choice}"
        opt = [o for o in rec.options if o.choice == "sleep"][0]
        assert any("isn't important" in r for r in opt.reasons)
        print("[SUCCESS] Recommender test 4: distraction -> sleep passed!")
    finally:
        store.close()
        os.remove(store.db_path)


def test_recommender_empty_history_never_crashes():
    store = make_store()
    try:
        rec = Recommender(store).recommend(
            make_task(), extension_available=True)
        assert rec.recommended_choice in ("sleep", "replan", "continue", "break")
        assert rec.limited_data is True
        # Every option must exist and be scored.
        assert {o.choice for o in rec.options} == {"sleep", "replan", "continue", "break"}
        print("[SUCCESS] Recommender test 5: empty history safe passed!")
    finally:
        store.close()
        os.remove(store.db_path)


# ===============================================================
# Explainer tests (design.md, explainer)
# ===============================================================

def test_explainer_labels_limited_data():
    from coach.schemas import Recommendation
    rec = Recommendation(
        recommended_choice="sleep", limited_data=True, continue_available=True)
    text = build_explanation(rec, make_task())
    assert "don't have enough history" in text
    print("[SUCCESS] Explainer test 1: limited-data label passed!")


def test_explainer_comparison_separates_estimates():
    lines = build_comparison(make_task(est_minutes=90),
                             extension_minutes=30,
                             extension_available=True)
    assert any("estimate" in l for l in lines["continue"])
    assert any("won't finish" in l for l in lines["continue"])
    assert any("estimate" in l for l in lines["sleep"])

    blocked = build_comparison(make_task(), extension_available=False)
    assert "Not available" in blocked["continue"][0]
    print("[SUCCESS] Explainer test 2: comparison estimates passed!")

if __name__ == "__main__":
    # Store tests
    test_save_and_reload_event()
    test_resolve_event()
    test_extension_used_tonight()
    test_outcomes_and_feedback_queue()
    test_replans()
    test_goals()
    test_category_rules_and_corrections()
    test_export_import_delete()
    test_corrupt_db_falls_back()
    # Classifier tests
    test_classifier_user_rule_wins()
    test_classifier_builtin_known_app()
    test_classifier_ambiguous_never_guessed()
    test_classifier_learns_from_history()
    test_classifier_correction_never_rewrites_history()
    # Recommender tests
    test_recommender_urgent_task_continue_wins()
    test_recommender_extension_used_blocks_continue()
    test_recommender_important_not_urgent_late_replans()
    test_recommender_sleep_wins_on_distraction()
    test_recommender_empty_history_never_crashes()
    # Explainer tests
    test_explainer_labels_limited_data()
    test_explainer_comparison_separates_estimates()
    print("\n[INFO] All coach tests completed successfully!")
