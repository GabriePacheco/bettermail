import unittest

from app.openai_service import (
    build_user_prompt,
    calculate_openai_cost,
    is_complete_email,
    is_refusal_response,
    is_rough_draft,
    safe_professional_fallback,
    source_requires_safety_transform,
)


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

    def test_compose_mode_uses_subject_and_preserves_outlook_signature(self):
        prompt = build_user_prompt(
            text="confirma la reunion del jueves",
            tone_description="profesional y claro",
            mode="compose_email",
            context="Reunion trimestral",
            has_signature=True,
        )

        self.assertIn("Reunion trimestral", prompt)
        self.assertIn("ya tiene una firma de Outlook", prompt)
        self.assertIn("No agregues despedida", prompt)

    def test_reply_and_compose_prompts_share_completion_rules(self):
        reply_prompt = build_user_prompt(
            text="",
            tone_description="profesional",
            mode="suggest_reply",
            context="Puedes enviar el informe hoy?",
        )
        compose_prompt = build_user_prompt(
            text="enviar el informe hoy",
            tone_description="profesional",
            mode="compose_email",
            context="Informe semanal",
        )

        for prompt in (reply_prompt, compose_prompt):
            self.assertIn("correo completo", prompt)
            self.assertIn("No inventes", prompt)
            self.assertIn("tono: profesional", prompt)

    def test_regeneration_requests_a_distinct_alternative(self):
        prompt = build_user_prompt(
            text="necesito el informe",
            tone_description="profesional",
            mode="compose_email",
            context=None,
            variation=2,
        )

        self.assertIn("alternativa claramente distinta", prompt)

    def test_detects_the_refusal_seen_in_outlook(self):
        self.assertTrue(
            is_refusal_response(
                "No es apropiado continuar con este tipo de lenguaje. "
                "Puedo ayudarte a redactar un mensaje profesional."
            )
        )

    def test_physical_threat_is_treated_as_material_to_neutralize(self):
        prompt = build_user_prompt(
            text="Manos te van a faltar para pelarme la verga",
            tone_description="profesional, claro y respetuoso",
            mode="compose_email",
            context=None,
        )

        self.assertIn("eliminalas por completo", prompt)
        self.assertIn("No rechaces", prompt)

    def test_spanish_threat_gets_a_spanish_safe_fallback(self):
        fallback = safe_professional_fallback(
            "Manos te van a faltar para pelarme la verga"
        )

        self.assertTrue(fallback.startswith("Estimado/a"))
        self.assertNotIn("manos", fallback.lower())
        self.assertIn("no estoy de acuerdo", fallback.lower())
        self.assertNotIn("asunto importante", fallback.lower())
        self.assertNotIn("solicitudes", fallback.lower())
        self.assertTrue(is_complete_email(fallback))

        plural_fallback = safe_professional_fallback(
            "Todos ustedes me pelan la verga"
        )
        self.assertTrue(plural_fallback.startswith("Estimados"))

    def test_hostile_insult_uses_the_safety_email_flow(self):
        self.assertTrue(
            source_requires_safety_transform("Todos ustedes me pelan la verga")
        )

    def test_short_generic_sentence_is_not_accepted_as_a_complete_email(self):
        self.assertFalse(
            is_complete_email(
                "Les solicito su atencion para tratar un asunto importante."
            )
        )

    def test_short_outlook_draft_is_expanded_as_a_complete_email(self):
        self.assertTrue(is_rough_draft("necesito el informe para manana"))


if __name__ == "__main__":
    unittest.main()
