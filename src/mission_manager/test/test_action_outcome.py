import unittest

from mission_manager.action_outcome import cancel_was_accepted, terminal_state


class ActionOutcomeTests(unittest.TestCase):
    def test_cancel_response_without_goal_is_rejected(self):
        self.assertFalse(
            cancel_was_accepted(
                0,
                [],
                'goal-a',
                success_code=0,
            )
        )

    def test_cancel_response_with_goal_is_accepted(self):
        self.assertTrue(
            cancel_was_accepted(
                0,
                ['goal-a'],
                'goal-a',
                success_code=0,
            )
        )

    def test_error_or_different_goal_does_not_confirm_cancel(self):
        self.assertFalse(
            cancel_was_accepted(
                1,
                ['goal-a'],
                'goal-a',
                success_code=0,
            )
        )
        self.assertFalse(
            cancel_was_accepted(
                0,
                ['goal-b'],
                'goal-a',
                success_code=0,
            )
        )

    def test_late_cancel_does_not_hide_successful_result(self):
        self.assertEqual(
            terminal_state(
                4,
                True,
                succeeded_status=4,
                canceled_status=5,
                aborted_status=6,
            ),
            'success',
        )

    def test_only_canceled_action_status_reports_canceled(self):
        self.assertEqual(
            terminal_state(
                5,
                False,
                succeeded_status=4,
                canceled_status=5,
                aborted_status=6,
            ),
            'canceled',
        )
        self.assertEqual(
            terminal_state(
                6,
                False,
                succeeded_status=4,
                canceled_status=5,
                aborted_status=6,
            ),
            'failed',
        )

    def test_nonterminal_result_keeps_manager_locked(self):
        self.assertIsNone(
            terminal_state(
                2,
                False,
                succeeded_status=4,
                canceled_status=5,
                aborted_status=6,
            )
        )


if __name__ == '__main__':
    unittest.main()
