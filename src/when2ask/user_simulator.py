"""LLM user with fixed private intent and scoped answers."""

USER_PROMPT = """You are the user who gave the robot its instruction.
Your complete intent is fixed for this episode. Answer the current question using that intent.
Return JSON with exactly one field, choices. Include exactly the requested_slots and their values.
Do not reveal any unrequested choice. Do not suggest actions or discuss the evaluator.
Example format: {"choices": {"requested_slot": "candidate_id"}}."""


class LlmUser:
    def __init__(self, client, sample):
        self.client, self.sample = client, sample

    def answer(self, question):
        requested = question["slots"]
        def validate(value):
            if not isinstance(value, dict) or set(value) != {"choices"} or not isinstance(value["choices"], dict):
                raise ValueError("User reply must contain only choices")
            if set(value["choices"]) != set(requested):
                raise ValueError("User reply must address only the requested slots")
            if any(v != self.sample.theta_star[s] for s, v in value["choices"].items()):
                raise ValueError("User reply must preserve the user's fixed intent")
            return value
        private = dict(initial_instruction=self.sample.u0, complete_intent=self.sample.theta_star,
                       available_choices=self.sample.slots, question=question["text"], requested_slots=requested)
        return self.client.request("user", "user_answer", USER_PROMPT, private, validate, actor="user_simulator")
