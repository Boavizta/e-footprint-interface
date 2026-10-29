
# Editing an existing model

The user already has a model, given below as JSON in the format above, and asks for a change to it. Answer with only the objects that change, in this shape:

{
  "changed": {
    "servers": [...], "genai_apis": [...], "jobs": [...], "journeys": [...], "usage_patterns": [...]
  },
  "removed": {"servers": [<names>], "genai_apis": [<names>], "jobs": [<names>], "journeys": [<names>], "usage_patterns": [<names>]},
  "note": "one sentence on what was changed and what was assumed"
}

Rules:
- Objects are matched by name within their section. A known name with fields sets those fields and leaves every other field as it is; an unknown name is a new object and must be complete, like in a generated model.
- A journey's `steps` and a step's `jobs` list all the children after the change, not only the new ones: a step left out of a journey, or a job left out of a step, is deleted unless another journey or step still uses it. List a job as many times as the step calls it. Jobs are top level: a new job goes under `"jobs"` and is then listed by name in its step.
- `removed` deletes objects by name; a server or API can only be removed once no job uses it, a journey once no usage pattern uses it.
- Never rename an object, never write `null`, never repeat an object that does not change. Leave out every section that has nothing in it.
- Not editable here: a usage pattern's `device`, `network`, `country` and `journey`, a job's `server` or `genai_api`, a server's `kind`, and jobs that show neither `server` nor `genai_api` (they are of another kind; list them in steps by name but do not change their fields). Say in the `note` when the request needs one of those changed by hand.
- Change only what the request asks for. Keep the `comments` rule for every number you set.

The current model follows as JSON.
