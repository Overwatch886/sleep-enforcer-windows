# Sleep Enforcer Habit Coach Plan

## 1. Purpose

Evolve Sleep Enforcer into a local-first sleep and habit decision assistant.

At bedtime, the product should understand what the user is doing, estimate whether continuing is useful or distracting, explain the likely consequences of sleeping versus continuing, and persuade the user toward the better choice.

The existing sleep-enforcement behavior remains the final safety mechanism when the user does not choose, when the configured grace period expires, or when the user chooses to follow enforcement.

This is a personal project. The goal is not to build a general-purpose surveillance or productivity platform. The goal is to help one user make better decisions about sleep, work, study, distractions, and personal goals.

## 2. SDLC Model

This project will use the **Big Bang SDLC model** because it has one primary developer, one primary stakeholder, low coordination overhead, and no immediate need for formal staged releases or parallel team handoffs.

Big Bang does not mean skipping requirements, design, safety checks, privacy boundaries, or testing. It means the project will move from a documented requirements baseline into one concentrated implementation effort, while allowing requirements and design to evolve when real usage reveals better information.

### Practical sequence

1. Document and review the product requirements.
2. Design the smallest coherent architecture for the agreed MVP.
3. Implement the decision engine, persistence, coaching flow, and enforcement integration as one focused build.
4. Run headless, integration, and manual tests.
5. Package a usable personal release.
6. Observe real usage and revise based on evidence.

Existing schedule calculations, countdown behavior, and enforcement tests are regression boundaries throughout the project.

## 3. Product Goals

1. Reduce unnecessary late-night exceptions without treating every exception as bad.
2. Help the user make decisions consistent with their goals, principles, health, work, and study obligations.
3. Learn from actual behavior and outcomes instead of relying only on fixed reason keywords.
4. Make recommendations explainable so the user can see why the app reached a conclusion.
5. Preserve user autonomy while retaining enforcement as a safety fallback.
6. Keep sensitive behavior data local by default.
7. Add optional backup or synchronization only after the local experience is useful and trustworthy.

## 4. User Problem

The current application mainly asks for a reason to stay awake and grants an extension when the reason matches an accepted keyword.

That approach has limitations:

- It does not understand what the user is actually doing.
- It treats all accepted reasons similarly.
- It cannot distinguish productive work from habitual distraction.
- It does not show the likely consequences of staying awake or sleeping.
- It can encourage users to find a reason that bypasses enforcement.
- It does not learn from what happened the next day.

The new product should turn the bedtime interruption into a transparent decision-support moment rather than only a permission check.

## 5. MVP Scope

The MVP includes a decision engine and rich bedtime coaching flow alongside the existing enforcement logic.

### Included in MVP

- Structured bedtime decision prompt replacing the current reason-only experience.
- User description or selection of what they are currently doing.
- Task attributes: category, urgency, importance, estimated duration, and optional goal or principle alignment.
- Local event history for schedules, activity categories, choices, extensions, replans, and outcomes.
- Lightweight active-process or application categorization when explicitly enabled.
- Time-of-day and prior-event pattern analysis.
- User feedback and correction of the app's classifications.
- Contextual recommendations using:
  - personal principles and goals,
  - previous behavior patterns,
  - likely work quality and timing.
- Comparison of likely consequences for continuing versus sleeping and replanning.
- User choices to:
  - follow the recommendation,
  - continue for a bounded extension,
  - replan for later,
  - correct the app's interpretation,
  - decline to provide details.
- Existing grace period, extension, break, countdown, and hibernation behavior as fallback.
- Explicit insufficient-data behavior for new users or sparse history.
- Local settings for coaching intensity and data collection categories.
- Local data export and import.

### Deferred to v1.1

The dashboard is essential for transparency, but it comes after the core decision flow has generated meaningful data.

The dashboard should show:

- Why recommendations were made.
- Activity classifications and confidence.
- Accepted and overridden recommendations.
- Sleep, extension, and late-night exception patterns.
- Replanning outcomes.
- Next-day consequences.
- User corrections and disputed classifications.
- Weekly patterns and trends.

### Deferred to v2 or later

- Optional encrypted cloud backup or synchronization.
- Cross-device identity and conflict resolution.
- External AI services or advanced predictive models.
- Automatic interpretation of private documents, messages, or arbitrary task content.
- General-purpose calendar and task-management integration.

## 6. Bedtime Coaching Flow

When the configured warning or bedtime state is reached:

1. The app opens a non-blocking coaching prompt.
2. The user describes or selects what they are doing.
3. The app displays its current interpretation, such as work, study, obligation, recovery, leisure, distraction, or unknown.
4. The app shows the evidence and confidence behind that interpretation.
5. The app evaluates the available choices:
   - sleep now,
   - replan for a later time,
   - continue for a bounded extension,
   - take a short break before deciding.
6. The app gives a recommendation using the most relevant combination of:
   - values and principles,
   - personal behavior patterns,
   - likely timing and performance.
7. The app compares likely outcomes.
8. The user chooses or declines to answer.
9. The selected outcome is handed to the existing enforcement state machine.
10. The app records the event and later allows outcome feedback.

### Example comparison

**If you continue:**

- Estimated completion benefit.
- Proposed extension length.
- Expected sleep reduction.
- Relevant historical risks, such as oversleeping or being late the next day.

**If you sleep and replan:**

- Proposed completion time.
- Expected rested-work benefit.
- Risk from delaying an urgent task.
- Evidence from previous similar decisions.

Predictions must be labeled as estimates, not guarantees. The app must not invent personal evidence when history is insufficient.

## 7. Functional Requirements

### FR-1: Bedtime decision session

When the configured warning or bedtime state is reached, the app shall open a non-blocking decision session using the existing Tkinter event loop rules.

The session shall show the current schedule, ask what the user is doing, and offer a way to proceed without answering.

### FR-2: Task and context capture

The user shall be able to enter a short task description and choose or confirm:

- category,
- urgency,
- importance,
- estimated duration,
- goal or principle alignment.

The user may mark the activity as a distraction, legitimate obligation, recovery need, or unknown.

### FR-3: Activity evidence

When enabled, the app may record privacy-minimized active-process metadata and map it to broad categories.

The MVP shall not capture:

- keystrokes,
- screenshots,
- message contents,
- document contents,
- passwords,
- raw browsing history.

Unknown activity must remain unknown rather than being presented as fact.

### FR-4: Personal pattern model

The app shall maintain a local profile derived from recorded events.

The profile may include:

- common late-night activities,
- time-of-day effectiveness,
- extension frequency,
- replan frequency,
- next-day effects,
- user corrections,
- user-reported regret or satisfaction.

Each inferred classification shall retain a confidence value and identify the evidence used to derive it.

### FR-5: Recommendation decision

For each session, the decision engine shall evaluate at least:

- sleep now,
- replan for later,
- continue for a bounded extension,
- take a short break before deciding.

The recommendation shall consider task urgency, importance, estimated duration, user goals or principles, current schedule, historical outcomes, and confidence in activity classification.

### FR-6: Consequence comparison

The UI shall explain both likely paths. Evidence from the user's history must be visually distinct from general estimates.

The app shall explicitly indicate when it has insufficient personal data.

### FR-7: Persuasive explanation

The engine shall choose a contextual explanation style:

- principle-based,
- pattern-based,
- optimization-based,
- or a combination.

Language shall be respectful, non-shaming, and transparent about uncertainty. The app shall not use threats, deception, or unsupported medical claims.

### FR-8: User choice and enforcement handoff

The user shall be able to accept the recommendation, continue within a bounded extension, replan, correct the classification, or dismiss coaching details.

After the choice, the existing enforcement state machine shall handle the selected outcome.

A refusal to answer shall not bypass enforcement.

### FR-9: Replanning

A replan choice shall create a local planned task with:

- target time,
- estimated duration,
- optional reminder,
- original bedtime decision reference.

The MVP shall not silently modify unrelated calendars.

### FR-10: Outcome feedback

After the decision window or following the wake period, the app shall offer lightweight feedback such as:

- completed,
- postponed,
- overslept,
- late,
- regretted staying up,
- recommendation was wrong.

The user may skip feedback. Feedback shall update future evidence without rewriting historical events.

### FR-11: Data controls

The user shall be able to:

- view what categories are being collected,
- disable activity categories,
- delete history,
- export local data,
- import a prior export.

Disabling data collection shall not disable the core sleep schedule or enforcement.

### FR-12: Dashboard v1.1

The later dashboard shall show the evidence used by recommendations and provide correction and deletion controls.

## 8. Non-Functional Requirements

- **Privacy:** local-first. Sensitive data stays on-device by default.
- **Explainability:** each recommendation exposes contributing factors and confidence.
- **Safety:** existing schedule, midnight rollover, countdown, break, and hibernation behavior remains regression-tested.
- **Responsiveness:** prompts and timers remain non-blocking.
- **Resilience:** missing or corrupt history falls back to safe enforcement behavior.
- **Accessibility:** keyboard navigation, readable text, and clear distinction between recommendation and enforcement.
- **Data minimization:** collect only signals needed for a declared recommendation or insight.
- **Portability:** continue supporting the Windows packaged application and existing app-data location.
- **Testability:** scoring and inference logic must be separate from Tkinter and testable headlessly.

## 9. User Stories and Acceptance Criteria

### US-1: Legitimate late work

As a user with a real deadline, I want to explain the task and receive a bounded plan so I can work without losing the entire night.

Acceptance criteria:

- An urgent task that fits within the allowed extension can receive a bounded extension recommendation.
- The app still shows the sleep cost and final cutoff.
- Existing enforcement resumes when the extension ends.

### US-2: Habitual distraction

As a user, I want repeated distraction patterns recognized without false certainty.

Acceptance criteria:

- Repeated events can produce a distraction classification with confidence.
- The app shows the relevant pattern evidence.
- The user can correct the classification.
- Corrections affect future scoring but do not alter historical events.

### US-3: Replan instead of forcing

As a user, I want a realistic later plan when continuing is unlikely to help.

Acceptance criteria:

- An important but non-urgent task during a historically low-performing period can produce a later recommendation.
- Selecting replan stores the task and returns to the sleep flow.

### US-4: Consequences

As a user, I want to compare likely results before choosing.

Acceptance criteria:

- The decision view presents continue and sleep/replan outcomes.
- Historical evidence is separate from generic estimates.
- Unknown evidence is explicitly labeled unknown.

### US-5: Privacy control

As a user, I want control over behavior data collection.

Acceptance criteria:

- Activity observation can be disabled while schedule enforcement remains active.
- Data can be inspected, exported, imported, and deleted.

### US-6: Insufficient data

As a new user, I want useful guidance before the app knows me well.

Acceptance criteria:

- With no history, the engine uses current task details and configured schedule only.
- The UI states that the recommendation is based on limited data.
- No fabricated personal pattern is displayed.

## 10. Success Measures

Initial targets to validate after instrumentation is available:

- At least 70% of recommendation decisions are accepted or followed by a replan.
- Repeated late-night exceptions decrease over a 2-4 week period without suppressing legitimate urgent work.
- User-reported sleep quality improves over a 2-4 week period.
- Users can identify the evidence behind a recommendation in usability testing.
- Distraction classification approaches 80% precision only after sufficient user feedback. This is not a launch guarantee.

## 11. Risks and Mitigations

### Wrong classification

Show confidence, allow correction, preserve overrides, and use conservative fallback behavior.

### Excessive surveillance

Minimize signals, make activity observation explicit, and provide deletion and export controls.

### Coercive persuasion

Show alternatives and evidence. Keep recommendations separate from the configured enforcement action.

### False predictions

Label estimates, require sufficient history, and avoid medical or legal claims.

### Scope creep

Keep the dashboard, cloud sync, external AI, and document-content understanding outside the MVP.

### Existing behavior regressions

Separate decision logic from Tkinter and keep current schedule tests passing throughout implementation.

## 12. Open Decisions Before Technical Design

These decisions will be resolved before the technical design is finalized:

1. Exact allowed process/application metadata categories and default privacy settings.
2. Whether a task description is required or structured tags alone are sufficient.
3. Maximum extension duration and whether multiple extensions are allowed.
4. Which next-day outcomes can be detected automatically versus user-reported.
5. Whether goals and principles use free text, predefined values, or both.
6. Whether MVP storage remains JSON or moves to SQLite. SQLite is recommended if event history grows beyond simple settings.
7. Minimum dashboard views for the v1.1 transparency release.
8. Whether cloud backup remains entirely deferred until after MVP or is represented by an interface during initial design.

## 13. Scope Boundary

This document defines what the product must do and why.

It does not yet define:

- class names,
- database tables,
- scoring formulas,
- UI pixel layouts,
- cloud provider,
- implementation sequence.

Those belong to the Technical Design phase after this requirements baseline is reviewed.
