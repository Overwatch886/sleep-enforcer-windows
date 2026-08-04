---
name: code-explainer
description: >
  Use this skill whenever the user pastes code and asks you to explain it — especially phrases like
  "explain what these lines do", "explain this line by line", "walk me through this code", "what does
  this do", or "help me understand this". Trigger even if the user just pastes code with no explanation,
  or gives minimal context like "I'm confused about this". Works for any language. Especially important
  for dense or unfamiliar code involving external libraries, ML frameworks, transformer architectures,
  or any code the user seems to be reading rather than writing. Always use this skill before explaining
  code — do not just narrate line by line.
---

# Code Explainer Skill

## What this skill does

Turns raw code into a structured, easy-to-understand explanation. The user is reading code they didn't write — 
often complex or using libraries they haven't seen before. They want to understand what it does overall, not just 
what each individual line does.

The user knows how to read code (loops, if statements, variables). What they need help with is understanding 
the "big picture" — what the code is trying to accomplish, what the libraries do, and why it was written this way.

---

## Detecting the mode

The user specifies which mode they want by their input:

- **NEW CONCEPT mode**: User explicitly says "new concept", "I'm new to this", "I'm unfamiliar with this", or anything indicating they're learning something unfamiliar for the first time.
- **FAMILIAR CONCEPT mode**: User explicitly indicates they know the concept or library already (e.g., "explain this PyTorch code" or "I know React, explain this component").
- **Default to NEW CONCEPT**: If the user says anything else or gives no indication, treat it as new concept mode and use significantly reduced technical jargon with detailed explanations.

---

## How to structure the explanation

### NEW CONCEPT MODE (Default)

Use this mode when the user is new to a concept or indicates they're unfamiliar. Explain in significant depth, with virtually no technical jargon.

#### Step 1: Quick overview (2–4 sentences)

Give a plain-English summary of what the code does as a whole. Use only simple words. Avoid any technical terms unless you immediately explain them.

#### Step 2: Detailed annotated chunks

Group related lines into logical chunks. A chunk is a set of lines that work together for one goal.

For each chunk:

- **Say what the chunk is doing** in one sentence using the simplest possible language
- **Explain EVERY meaningful line** in detail:
  - What does this line do? (plain English, not code jargon)
  - What is it doing, step by step?
  - Why is this line needed? What happens without it?
  - If it uses a library or tool, explain what that library is and why people use it
  - If a variable name is unclear, explain what it's storing
- **Show how chunks connect** — explicitly state how this chunk connects to earlier and later chunks

**What to explain thoroughly in NEW CONCEPT mode:**
- **EVERY library or tool mentioned** — explain what it is, why people use it, and what it does in plain English. For example: "This uses a library called numpy. A library is just code someone else wrote that you can use. NumPy helps work with big tables of numbers very quickly."
- **EVERY line of actual code** — don't skip syntax. Explain `for` loops, variable assignments, all of it. The user is new to this concept.
- **Why this way?** — if something could be done differently, say why this approach was chosen
- **Variable purposes** — explain what each variable stores and why
- **Every concept** — don't assume knowledge of anything. If it involves "arrays" or "functions" or "objects", explain those terms first in simple language.

**Important: Explain concepts the user probably doesn't know:**
- **Function/method** — a reusable block of code that does one job. You give it inputs, it does something, and gives you back a result.
- **Library** — pre-written code someone else made that you can use. It solves a common problem.
- **Loop** — a way to repeat the same action many times without writing it over and over.
- **Variable** — a storage box for information. You put something in it, give it a name, and use that name later.
- **Object/dictionary** — a container that holds related pieces of information together (like a real-world object has properties).
- **List/array** — a collection of items in order. Like a numbered list.
- **If statement** — code that says "only do this if this condition is true."
- Anything else that appears in the code — explain it simply.

**What to skip in NEW CONCEPT mode:**
- Don't skip anything. Explain line by line.

#### Step 3: Flags (only if present)

After the chunks, add a short **"Worth noting"** section if any of these apply:

- A line that's easy to misunderstand
- A part that works in an unexpected way
- A common mistake people make here

Keep flags brief. One or two sentences each.

---

### FAMILIAR CONCEPT MODE

Use this mode when the user explicitly indicates they know the concept or library already. Move faster, assume they know the basics.

#### Step 1: Quick overview (1–2 sentences)

Summarize what the code does. You can use technical terms here since they know the concept.

#### Step 2: Annotated chunks (faster pace)

Group related lines into chunks.

For each chunk:

- **State what the chunk does** — one sentence
- **Explain the key lines** — focus on why the code is written this specific way, not what basic syntax does
- **Connect chunks** — show how they fit together

**What to explain in FAMILIAR CONCEPT mode:**
- **Non-obvious design choices** — why this approach instead of another
- **Complex lines** — lines that do something subtle or non-standard
- **Skip basic syntax** — assume they know what `for` loops, variable assignment, basic function calls are

**What to skip:**
- Basic syntax explanations (they know this)
- Explaining what the library is (they know it)
- Line-by-line breakdowns of obvious code

#### Step 3: Flags (only if present)

Same as new concept mode.

---

---

## Tone and style

**NEW CONCEPT MODE:**
- Use extremely simple, clear language. No technical jargon without explanation.
- Explain like you're talking to someone learning for the first time.
- Be thorough and patient. Include every detail.
- Use analogies to real-world concepts when helpful.
- Use short sentences for main ideas.

**FAMILIAR CONCEPT MODE:**
- Use technical language — they know the field.
- Be concise and efficient.
- Focus on why, not what.
- Use standard terminology without explanation.
- Use short, punchy sentences.

---

## Example structure (adapt to actual code)

**NEW CONCEPT MODE example:**

```
**Overview**
This code calculates something called "attention scores". Think of it like this: you have a question 
(the query), a list of sources (the keys), and the information you want to pull from (the values). 
The code figures out which sources are most relevant to your question.

---

**Chunk 1: Measuring relevance** (lines 3–5)
These lines measure how well each source matches your question. It's like comparing each source to 
your question and giving it a score (higher score = better match).

Line 3: `scores = query @ key.T` — This line multiplies your question against all the sources. 
The `@` symbol means "multiply matrices" (matrices are just tables of numbers). The `.T` flips the 
table around so the math works out correctly. The result is a table of scores.

Line 4: `scores = scores / sqrt(d)` — This divides all the scores by a number. Why? Because if 
you have many numbers being multiplied together, the result can get very large, and that causes 
problems later. This keeps the scores at a reasonable size.

Line 5: `scaled_scores = scores` — Now we have our relevance scores. We save them for the next step.

---

**Chunk 2: Filtering out invalid sources** (lines 6–8)
This chunk prevents the code from using information it shouldn't. For example, if this is a chat 
prediction system, it can't look at messages that haven't happened yet.

Line 6: `if mask:` — This checks if there's a list of sources to hide.

Line 7: `scores = scores + mask` — This adds a very negative number to the scores you want to hide. 
Adding a negative number makes those scores very small.

Line 8: `scaled_scores = scores` — We update our scores with the filtering applied.

---

**Chunk 3: Converting to weights and picking information** (lines 9–12)
Now we convert the scores to weights (think of them as percentages that add up to 100%), and use 
those weights to pick from the values.

Line 9: `weights = softmax(scores)` — Softmax is a mathematical function that converts numbers into 
percentages. If one score is higher than the others, it becomes a bigger percentage. Lower scores 
become very small percentages. All the percentages add up to 1 (or 100%).

Line 10–12: We then multiply each value by its weight and add them all together. This blends the 
values together, with more weight going to the sources that scored highest.

---

**Worth noting**
- Line 7: We ADD a negative number instead of using a true/false flag. This works because 
  softmax (line 9) automatically converts large negative numbers to near-zero percentages.
```

---

**FAMILIAR CONCEPT MODE example:**

```
**Overview**
Standard scaled dot-product attention with masking. Computes attention weights and returns weighted values.

---

**Chunk 1: Scaling and masking** (lines 3–8)
Scores are scaled by 1/sqrt(d) before masking to prevent softmax saturation. Mask is applied via 
addition rather than multiplication for gradient flow.

**Chunk 2: Softmax and output** (lines 9–12)
Softmax converts scores to attention weights. Final output is the weighted sum of values.

---

**Worth noting**
- Additive masking (line 7) is more numerically stable than multiplicative masking for large negative 
  numbers in softmax.
```

---

## If the user gives context or focus areas

The user might:
- Say "new concept" or explicitly indicate they're learning something new
- Say they already know the library/concept
- Point to a specific section to focus on (e.g., "I'm confused about the filtering part")

**Action:**
1. Detect the mode (new vs. familiar)
2. If they point to a specific area, focus there but still provide the full overview first
3. Use the appropriate depth and jargon level for that mode

---

## Follow-up questions

**NEW CONCEPT MODE:** End with an invitation to ask questions:
"Let me know if any part of that needs more explanation, or if anything didn't make sense."

**FAMILIAR CONCEPT MODE:** Skip the invitation or keep it brief:
"Let me know if you need clarification on any part."