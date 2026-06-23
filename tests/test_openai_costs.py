import unittest

from app.openai_service import build_user_prompt, calculate_openai_cost


class OpenAICostTests(unittest.TestCase):
    def test_calculates_uncached_input_and_output_cost(self):
        cost = calculate_openai_cost(
            prompt_tokens=1_000,
            cached_prompt_tokens=0,
            completion_tokens=500,
            input_cost_per_1m_usd=0.40,
            cached_input_cost_per_1m_usd=0.10,
            output_cost_per_1m_usd=1.60,
        )

        self.assertEqual(cost, 0.0012)

    def test_applies_cached_input_rate(self):
        cost = calculate_openai_cost(
            prompt_tokens=1_000,
            cached_prompt_tokens=600,
            completion_tokens=0,
            input_cost_per_1m_usd=0.40,
            cached_input_cost_per_1m_usd=0.10,
            output_cost_per_1m_usd=1.60,
        )

        self.assertEqual(cost, 0.00022)

    def test_caps_cached_tokens_at_prompt_total(self):
        cost = calculate_openai_cost(
            prompt_tokens=100,
            cached_prompt_tokens=500,
            completion_tokens=0,
            input_cost_per_1m_usd=0.40,
            cached_input_cost_per_1m_usd=0.10,
            output_cost_per_1m_usd=1.60,
        )

        self.assertEqual(cost, 0.00001)

    def test_compose_mode_builds_a_complete_email_from_rough_ideas(self):
        prompt = build_user_prompt(
            text="necesito el informe para manana",
            tone_description="profesional y claro",
            mode="compose_email",
            context=None,
        )

        self.assertIn("Redacta un correo completo", prompt)
        self.assertIn("borrador de ideas", prompt)
        self.assertIn("saludo neutro", prompt)

    def test_regeneration_requests_a_distinct_alternative(self):
        prompt = build_user_prompt(
            text="necesito el informe",
            tone_description="profesional",
            mode="compose_email",
            context=None,
            variation=2,
        )

        self.assertIn("alternativa claramente distinta", prompt)


if __name__ == "__main__":
    unittest.main()
